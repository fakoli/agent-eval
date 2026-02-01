# Security Reference

Security patterns and principles for Python/FastAPI backends. Security is not an afterthought—it is integrated from the very beginning of the development lifecycle.

## Core Security Philosophy

### Secure by Design
Security considerations are integrated at the start, not retrofitted. Before writing code:
1. Document the threat model
2. Identify attack surfaces
3. Define security requirements alongside functional requirements
4. Review design decisions for security implications

### Defense in Depth
Never rely on a single security control. Layer multiple controls so that if one fails, others still protect the system:
- Authentication + Authorization + Input Validation + Output Encoding
- Network segmentation + Application firewalls + Rate limiting
- Encryption at rest + Encryption in transit + Access controls

---

## Least Privilege

### Principle
Users, services, and workflows receive exactly the minimum permissions required to perform their tasks—nothing more.

### Implementation Patterns

#### Role-Based Access Control (RBAC)
```python
from enum import Enum
from typing import Set

class Permission(str, Enum):
    READ_OWN = "read:own"
    READ_ANY = "read:any"
    WRITE_OWN = "write:own"
    WRITE_ANY = "write:any"
    DELETE_OWN = "delete:own"
    DELETE_ANY = "delete:any"
    ADMIN = "admin"

class Role(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.USER: {Permission.READ_OWN, Permission.WRITE_OWN, Permission.DELETE_OWN},
    Role.MODERATOR: {Permission.READ_OWN, Permission.READ_ANY, Permission.WRITE_OWN},
    Role.ADMIN: set(Permission),  # All permissions
}
```

#### Resource-Level Authorization
```python
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    document = await db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404)
    
    # Verify ownership OR elevated permission
    if document.owner_id != current_user.id:
        if Permission.READ_ANY not in current_user.permissions:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return document
```

#### Privilege Escalation Auditing
```python
from datetime import datetime

async def elevate_privilege(
    user_id: str,
    new_role: Role,
    reason: str,
    granted_by: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Log the escalation
    audit_log = AuditLog(
        action="PRIVILEGE_ESCALATION",
        target_user_id=user_id,
        previous_role=user.role,
        new_role=new_role,
        reason=reason,
        granted_by_id=granted_by.id,
        timestamp=datetime.utcnow(),
        ip_address=request.client.host,
    )
    db.add(audit_log)
    
    # Apply the change
    user.role = new_role
    await db.commit()
```

#### Service-to-Service Least Privilege
```python
# Each service has scoped credentials
SERVICE_SCOPES = {
    "user-service": ["users:read", "users:write"],
    "billing-service": ["users:read", "payments:*"],
    "analytics-service": ["events:write"],  # Write-only, cannot read user data
}
```

---

## Input Validation and Sanitization

### Principle
All input is untrusted. Validate structure, type, length, and format. Sanitize to prevent injection attacks.

### Validation Patterns

#### Pydantic with Strict Validation
```python
from pydantic import BaseModel, Field, validator, EmailStr
import re

class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    bio: str | None = Field(default=None, max_length=500)
    
    @validator("username")
    def username_not_reserved(cls, v):
        reserved = {"admin", "root", "system", "api", "null", "undefined"}
        if v.lower() in reserved:
            raise ValueError("Username is reserved")
        return v
    
    @validator("bio")
    def sanitize_bio(cls, v):
        if v is None:
            return v
        # Strip potentially dangerous content
        return bleach.clean(v, tags=[], strip=True)
```

#### SQL Injection Prevention
```python
# NEVER: String interpolation
query = f"SELECT * FROM users WHERE id = '{user_id}'"  # VULNERABLE

# ALWAYS: Parameterized queries
result = await db.execute(
    select(User).where(User.id == user_id)  # SQLAlchemy ORM
)

# Or with raw SQL
result = await db.execute(
    text("SELECT * FROM users WHERE id = :user_id"),
    {"user_id": user_id}
)
```

#### XSS Prevention
```python
import html
from markupsafe import escape

# Escape user content before rendering
def render_comment(comment: str) -> str:
    return html.escape(comment)

# For templates (Jinja2 auto-escapes by default)
# But be explicit when needed:
{{ user_input | e }}
```

#### Command Injection Prevention
```python
import subprocess
import shlex

# NEVER: Shell=True with user input
subprocess.run(f"convert {user_filename}", shell=True)  # VULNERABLE

# ALWAYS: Use argument lists
subprocess.run(
    ["convert", validated_filename],
    shell=False,
    capture_output=True,
)

# If shell is required, use shlex.quote
safe_arg = shlex.quote(user_input)
```

#### Path Traversal Prevention
```python
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads")

def safe_file_path(filename: str) -> Path:
    # Resolve to absolute path and verify it's within allowed directory
    safe_name = Path(filename).name  # Strip directory components
    full_path = (UPLOAD_DIR / safe_name).resolve()
    
    if not full_path.is_relative_to(UPLOAD_DIR):
        raise ValueError("Invalid file path")
    
    return full_path
```

---

## Whitelist Over Blacklist

### Principle
In sandboxed or restricted environments, explicitly allow known-good values rather than blocking known-bad values. Blacklists are incomplete by definition.

### Implementation Patterns

#### Allowed File Types
```python
# Whitelist approach (preferred)
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "text/plain",
}

def validate_upload(file: UploadFile) -> bool:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {ext} not allowed")
    
    # Also verify MIME type (don't trust extension alone)
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "Invalid file type")
    
    return True
```

#### Sandboxed Code Execution (REPL)
```python
# Whitelist allowed built-ins
SAFE_BUILTINS = {
    "abs", "all", "any", "bool", "dict", "enumerate",
    "filter", "float", "int", "len", "list", "map",
    "max", "min", "print", "range", "round", "set",
    "sorted", "str", "sum", "tuple", "zip",
}

# Whitelist allowed modules
SAFE_MODULES = {"math", "json", "datetime", "collections"}

def create_sandbox():
    safe_globals = {
        "__builtins__": {k: getattr(__builtins__, k) for k in SAFE_BUILTINS},
    }
    # Import only allowed modules
    for mod_name in SAFE_MODULES:
        safe_globals[mod_name] = __import__(mod_name)
    return safe_globals

def execute_sandboxed(code: str, timeout: float = 5.0):
    sandbox = create_sandbox()
    # Execute with restricted globals
    exec(compile(code, "<sandbox>", "exec"), sandbox)
```

#### API Endpoint Allowlisting
```python
# For proxies or API gateways
ALLOWED_ENDPOINTS = {
    "/api/v1/users",
    "/api/v1/products",
    "/api/v1/orders",
}

def validate_proxy_target(path: str) -> bool:
    # Normalize and check against whitelist
    normalized = path.rstrip("/").lower()
    return normalized in ALLOWED_ENDPOINTS
```

---

## Secure File Handling

### Principle
File uploads are a significant attack vector. Validate, sanitize, and isolate uploaded files.

### Implementation Patterns

#### Comprehensive Upload Validation
```python
import magic
import hashlib
from pathlib import Path

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

async def secure_upload(file: UploadFile) -> str:
    # 1. Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # 2. Verify extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed")
    
    # 3. Verify actual MIME type (not just header)
    detected_mime = magic.from_buffer(contents, mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "File content type not allowed")
    
    # 4. Verify extension matches content
    if ALLOWED_MIME_TYPES[detected_mime] != ext:
        raise HTTPException(400, "File extension does not match content")
    
    # 5. Generate safe filename (never use user-provided name directly)
    file_hash = hashlib.sha256(contents).hexdigest()[:16]
    safe_filename = f"{file_hash}{ext}"
    
    # 6. Store outside web root
    storage_path = Path("/app/uploads") / safe_filename
    storage_path.write_bytes(contents)
    
    return safe_filename
```

#### Prevent Directory Traversal
```python
def get_user_file(user_id: str, filename: str) -> Path:
    # User files are isolated by user_id
    user_dir = UPLOAD_ROOT / str(user_id)
    
    # Resolve and validate path
    requested_path = (user_dir / filename).resolve()
    
    if not requested_path.is_relative_to(user_dir):
        raise HTTPException(403, "Access denied")
    
    if not requested_path.exists():
        raise HTTPException(404, "File not found")
    
    return requested_path
```

#### Executable File Prevention
```python
DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".so", ".sh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".py", ".php", ".asp",
    ".jsp", ".jar", ".war", ".html", ".htm", ".svg",
}

def is_safe_filename(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    # Also check for double extensions like file.pdf.exe
    all_suffixes = Path(filename).suffixes
    return not any(s.lower() in DANGEROUS_EXTENSIONS for s in all_suffixes)
```

---

## Secure Error Handling

### Principle
Error messages should help users without helping attackers. Never expose internal system details, stack traces, or implementation specifics.

### Implementation Patterns

#### Exception Handler Middleware
```python
from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import uuid

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Generate correlation ID for debugging
    error_id = str(uuid.uuid4())
    
    # Log full details internally
    logger.error(
        f"Unhandled exception [error_id={error_id}]",
        exc_info=exc,
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Return safe message to client
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "error_id": error_id,  # For support reference
            }
        }
    )
```

#### Custom Exception Classes
```python
class AppException(Exception):
    """Base exception with safe public message."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    public_message: str = "An error occurred"
    
    def __init__(self, internal_message: str | None = None):
        self.internal_message = internal_message
        super().__init__(internal_message or self.public_message)

class UserNotFoundError(AppException):
    status_code = 404
    error_code = "USER_NOT_FOUND"
    public_message = "User not found"

class AuthenticationError(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    public_message = "Authentication failed"  # Don't say "wrong password"

class RateLimitError(AppException):
    status_code = 429
    error_code = "RATE_LIMITED"
    public_message = "Too many requests"
```

#### Safe vs Unsafe Error Messages
```python
# UNSAFE - Reveals system details
"Database connection failed: PostgreSQL server at db.internal:5432 refused connection"
"User admin@company.com not found in table users"
"File /etc/passwd cannot be read: permission denied"
"SQL syntax error near 'SELECT * FROM users WHERE'"

# SAFE - Generic, actionable
"Service temporarily unavailable"
"Invalid credentials"
"File not found"
"Invalid request"
```

#### Debug Mode Protection
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    debug: bool = False
    environment: str = "production"

settings = Settings()

# Never enable debug in production
if settings.environment == "production" and settings.debug:
    raise RuntimeError("Debug mode cannot be enabled in production")

# Conditional detail in responses
def get_error_detail(exc: Exception) -> dict:
    base = {"code": "ERROR", "message": "An error occurred"}
    if settings.debug:
        base["debug"] = {"type": type(exc).__name__, "detail": str(exc)}
    return base
```

---

## Threat Modeling

### When to Document
- Before starting new service or feature design
- When adding authentication/authorization flows
- When handling sensitive data (PII, financial, health)
- When exposing new API endpoints

### Template
```markdown
## Threat Model: [Feature Name]

### Assets
- What are we protecting? (user data, credentials, system access)

### Trust Boundaries
- Where does trusted become untrusted? (API gateway, database, external services)

### Entry Points
- How can attackers interact? (API endpoints, file uploads, webhooks)

### Threats (STRIDE)
- **S**poofing: Can attackers impersonate users/services?
- **T**ampering: Can data be modified in transit/at rest?
- **R**epudiation: Can actions be denied? Do we have audit logs?
- **I**nformation Disclosure: Can sensitive data leak?
- **D**enial of Service: Can the service be overwhelmed?
- **E**levation of Privilege: Can users gain unauthorized access?

### Mitigations
| Threat | Mitigation | Status |
|--------|------------|--------|
| SQL Injection | Parameterized queries | Implemented |
| XSS | Output encoding, CSP | Implemented |

### Residual Risks
- Accepted risks with justification
```
