# API Design Reference

Comprehensive patterns for API design in Python backends.

## Protocol Selection

Choose the right protocol for the communication context:

| Protocol | Use Case | When to Choose |
|----------|----------|----------------|
| **REST** | External APIs, client-to-backend | Default choice. Simple, cacheable, widely understood |
| **GraphQL** | Flexible data fetching, mobile clients | Clients need exactly the data they request, reduce over/under-fetching |
| **gRPC** | Internal microservice communication | High performance required, you control both ends |

### REST (Default for External APIs)
- Resource-based URLs with standard HTTP methods
- Cacheable via HTTP headers
- Works with any client (browsers, mobile, CLI)
- Stateless by design

### GraphQL (Flexible Client Needs)
- Single endpoint, client specifies exact fields needed
- Reduces round trips for complex data requirements
- **N+1 Problem**: Use DataLoaders for batching database queries
- **Field-Level Authorization**: Implement in resolvers, not middleware
- Higher backend complexity—justify the trade-off

### gRPC (Internal Services)
- Binary Protocol Buffers format—faster serialization than JSON
- Strong typing via `.proto` schema definitions
- Bi-directional streaming support
- Requires control of both client and server
- Not suitable for browser clients without proxy

```protobuf
// Example: internal user service
service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (stream User);
}
```

---

## REST Resource Conventions

### URL Structure
- Resources are nouns: `/users`, `/orders`, `/products`
- Plural names: `/users/{id}` not `/user/{id}`
- Nested for ownership: `/users/{id}/orders`
- Actions as sub-resources when needed: `/orders/{id}/cancel` (POST)
- Max 2-3 levels of nesting; beyond that, flatten with query params

### Input Handling

**Path Parameters** — Required identifiers for specific resources:
```
GET /events/123           # Event ID is required
GET /users/456/orders/789 # Both IDs required
```

**Query Parameters** — Optional filters and refinements:
```
GET /events?location=LA&date=2024-01-01&status=active
GET /users?role=admin&sort=-created_at&limit=20
```

**Request Body** — Data for creation/updates (POST, PUT, PATCH):
```python
@router.post("/events")
async def create_event(event: CreateEventRequest):  # Body
    ...

@router.patch("/events/{event_id}")
async def update_event(
    event_id: str,           # Path - required
    updates: UpdateEventRequest,  # Body - the changes
):
    ...
```

### HTTP Methods
| Method | Purpose | Idempotent | Safe |
|--------|---------|------------|------|
| GET | Read resource(s) | Yes | Yes |
| POST | Create resource | No | No |
| PUT | Replace entire resource | Yes | No |
| PATCH | Partial update | Yes | No |
| DELETE | Remove resource | Yes | No |

### Status Codes
```
2xx Success
  200 OK - General success, GET/PUT/PATCH
  201 Created - POST success, include Location header
  204 No Content - DELETE success, no body

4xx Client Errors
  400 Bad Request - Malformed syntax, validation failure
  401 Unauthorized - Missing/invalid authentication
  403 Forbidden - Authenticated but not permitted
  404 Not Found - Resource doesn't exist
  409 Conflict - State conflict (duplicate, version mismatch)
  422 Unprocessable Entity - Valid syntax, semantic errors

5xx Server Errors
  500 Internal Server Error - Unexpected failures
  502 Bad Gateway - Upstream service failure
  503 Service Unavailable - Temporary overload/maintenance
  504 Gateway Timeout - Upstream timeout
```

## Response Envelope Standards

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Collection Response
```json
{
  "data": [ ... ],
  "meta": {
    "total_count": 142,
    "page": 1,
    "page_size": 20,
    "has_more": true
  },
  "links": {
    "self": "/users?page=1",
    "next": "/users?page=2",
    "prev": null
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

## Pagination Patterns

### Offset-Based (Simple)
```
GET /users?limit=20&offset=40
```
- Pros: Simple, random access
- Cons: Performance degrades on large offsets, inconsistent with concurrent writes

### Cursor-Based (Recommended)
```
GET /users?limit=20&cursor=eyJpZCI6MTAwfQ==
```
- Pros: Consistent results, efficient on large datasets
- Cons: No random access, requires stable sort order

### Implementation
```python
@router.get("/users")
async def list_users(
    limit: int = Query(default=20, le=100),
    cursor: str | None = Query(default=None),
) -> PaginatedResponse[User]:
    # Decode cursor, query with WHERE id > cursor_id
    # Encode next cursor from last item
```

## Filtering and Search

### Query Parameters
```
GET /orders?status=pending&created_after=2024-01-01
GET /products?category=electronics&price_min=100&price_max=500
GET /users?q=john&sort=-created_at
```

### Conventions
- Use snake_case for parameter names
- Prefix date ranges: `created_after`, `created_before`
- Prefix numeric ranges: `price_min`, `price_max`
- Use `-` prefix for descending sort: `sort=-created_at`
- Multiple values: `status=pending,processing` or `status[]=pending&status[]=processing`

## Versioning Strategy

### URL Path (Recommended)
```
/api/v1/users
/api/v2/users
```

### Rules
- Major version in URL for breaking changes
- Support N-1 versions minimum (current + previous)
- 6-month minimum deprecation notice
- Document all breaking changes in CHANGELOG

### Header-Based (Alternative)
```
Accept: application/vnd.api+json; version=2
```

## Request Validation

### Pydantic Models
```python
class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    
    model_config = ConfigDict(str_strip_whitespace=True)

class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
```

### Validation Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {"field": "email", "message": "Invalid email format"},
      {"field": "age", "message": "Must be >= 0"}
    ]
  }
}
```

## Rate Limiting

### Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640000000
Retry-After: 60  # On 429 response
```

### Response (429)
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "retry_after": 60
    }
  }
}
```

## Authentication Patterns

### Bearer Token (JWT)
```
Authorization: Bearer <jwt_token>
```
- Stateless—token contains claims
- Include expiration, issued-at, user ID, roles
- Validate signature on every request

### Session Token
```
Authorization: Bearer <session_id>
# or
Cookie: session_id=<session_id>
```
- Server stores session state
- Better for web apps with same-origin requests

### API Key (Service-to-Service)
```
X-API-Key: <key>
```
- For server-to-server communication
- Scope keys to specific permissions

### Error Responses
- 401 for missing/invalid credentials
- 403 for valid credentials but insufficient permissions
- Include `WWW-Authenticate` header on 401

## Authorization Patterns

### Role-Based Actions
```python
# Define which roles can perform which actions
PERMISSIONS = {
    "create_event": ["admin", "organizer"],
    "delete_event": ["admin"],
    "view_event": ["admin", "organizer", "user"],
}

async def require_permission(permission: str):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in PERMISSIONS.get(permission, []):
            raise HTTPException(403, "Insufficient permissions")
        return current_user
    return checker
```

### Resource Ownership (Critical)
```python
# NEVER trust client-provided user IDs for authorization
@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),  # From token, NOT request
):
    event = await get_event(event_id)
    
    # Verify ownership OR admin role
    if event.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Not authorized to delete this event")
    
    await delete_event(event_id)
```

## HATEOAS Links (When Complexity Warrants)

```json
{
  "data": {
    "id": "123",
    "status": "pending"
  },
  "links": {
    "self": "/orders/123",
    "cancel": "/orders/123/cancel",
    "payment": "/orders/123/payment"
  }
}
```

## Idempotency

### Idempotency Key Header
```
Idempotency-Key: <client-generated-uuid>
```

### Implementation
- Store key + response for configured TTL (24-48 hours)
- Return cached response on duplicate key
- Required for POST, optional for others

## Bulk Operations

### Batch Create
```
POST /users/batch
{
  "items": [
    {"email": "a@example.com", "name": "A"},
    {"email": "b@example.com", "name": "B"}
  ]
}
```

### Response
```json
{
  "data": {
    "succeeded": [{"id": "1", "email": "a@example.com"}],
    "failed": [
      {"index": 1, "error": {"code": "DUPLICATE", "message": "Email exists"}}
    ]
  },
  "meta": {
    "total": 2,
    "succeeded": 1,
    "failed": 1
  }
}
```

## OpenAPI Documentation

### FastAPI Conventions
```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Creates a user account with the provided details.",
    responses={
        409: {"model": ErrorResponse, "description": "Email already exists"}
    }
)
async def create_user(request: CreateUserRequest) -> UserResponse:
    ...
```

### Tags and Grouping
```python
router = APIRouter(prefix="/users", tags=["Users"])
```

---

## GraphQL Patterns (When Applicable)

Use GraphQL when clients need flexible data fetching. Be aware of the trade-offs.

### N+1 Query Problem
```python
# Problem: Each event resolver queries venue separately
# events(10) → 10 separate venue queries

# Solution: Use DataLoader for batching
from aiodataloader import DataLoader

async def batch_load_venues(venue_ids: list[str]) -> list[Venue]:
    venues = await db.query(Venue).filter(Venue.id.in_(venue_ids)).all()
    venue_map = {v.id: v for v in venues}
    return [venue_map.get(id) for id in venue_ids]

venue_loader = DataLoader(batch_load_venues)

# In resolver
async def resolve_venue(event, info):
    return await venue_loader.load(event.venue_id)
```

### Field-Level Authorization
```python
@strawberry.type
class User:
    id: str
    name: str
    
    @strawberry.field
    async def email(self, info) -> str | None:
        current_user = info.context.user
        # Only return email if viewing own profile or admin
        if current_user.id == self.id or current_user.role == "admin":
            return self._email
        return None
    
    @strawberry.field
    async def salary(self, info) -> float | None:
        # Only HR and admins can see salary
        if info.context.user.role not in ["hr", "admin"]:
            raise PermissionError("Not authorized")
        return self._salary
```

---

## gRPC Patterns (Internal Services)

Use gRPC for high-performance internal microservice communication.

### Proto Definition
```protobuf
syntax = "proto3";
package users;

service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc CreateUser(CreateUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (stream User);
}

message GetUserRequest {
  string user_id = 1;
}

message User {
  string id = 1;
  string email = 2;
  string name = 3;
  int64 created_at = 4;
}
```

### Python Server
```python
import grpc
from concurrent import futures
import users_pb2_grpc as users_grpc

class UserServicer(users_grpc.UserServiceServicer):
    async def GetUser(self, request, context):
        user = await db.get(User, request.user_id)
        if not user:
            context.abort(grpc.StatusCode.NOT_FOUND, "User not found")
        return user.to_proto()

server = grpc.aio.server()
users_grpc.add_UserServiceServicer_to_server(UserServicer(), server)
```

### When to Choose gRPC over REST
- Internal service-to-service calls (not browser clients)
- High throughput requirements (binary format ~10x smaller)
- Bi-directional streaming needed
- Strong typing required across services
- You control both client and server
