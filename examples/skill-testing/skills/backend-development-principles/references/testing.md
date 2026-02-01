# Testing Reference

Comprehensive testing patterns for Python/FastAPI backends.

## Testing Pyramid

```
        /\
       /  \      E2E Tests (few)
      /----\     Critical user journeys only
     /      \
    /--------\   Integration Tests (moderate)
   /          \  Database, external services
  /------------\ 
 /              \ Unit Tests (many)
/________________\ Domain logic, pure functions
```

## Coverage Targets

| Layer | Target | Rationale |
|-------|--------|-----------|
| Domain logic | 80%+ | Core business rules must be reliable |
| Infrastructure | 60%+ | Integration points need coverage |
| API routes | 50%+ | Thin layer, tested via integration |
| Overall | 60%+ | Balance thoroughness with maintenance cost |

## Test Structure

### Arrange-Act-Assert
```python
def test_user_creation_with_valid_email():
    # Arrange
    user_data = {"email": "test@example.com", "name": "Test User"}
    service = UserService(repository=mock_repo)
    
    # Act
    result = service.create_user(user_data)
    
    # Assert
    assert result.email == "test@example.com"
    assert result.id is not None
```

### Given-When-Then (BDD Style)
```python
def test_order_cancellation_refunds_payment():
    """
    Given an order with completed payment
    When the order is cancelled within 24 hours
    Then the payment should be refunded
    """
    order = create_paid_order(hours_ago=12)
    
    order.cancel()
    
    assert order.status == OrderStatus.CANCELLED
    assert order.payment.status == PaymentStatus.REFUNDED
```

## File-Scoped Commands

### Single Test File
```bash
pytest tests/unit/test_user_service.py -v
```

### Single Test Function
```bash
pytest tests/unit/test_user_service.py::test_create_user -v
```

### With Coverage
```bash
pytest tests/unit/test_user_service.py --cov=src/domain/user --cov-report=term-missing
```

### Parallel Execution
```bash
pytest tests/unit/ -n auto  # Requires pytest-xdist
```

### Skip Slow Tests
```bash
pytest tests/ -m "not slow"
```

## Fixtures

### Factory Pattern (Recommended)
```python
# conftest.py
import factory
from src.domain.user import User

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.id}@example.com")
    name = factory.Faker("name")
    created_at = factory.LazyFunction(datetime.utcnow)

# Usage in tests
def test_user_deactivation():
    user = UserFactory(status="active")
    user.deactivate()
    assert user.status == "inactive"
```

### Database Fixtures
```python
@pytest.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def user_in_db(db_session):
    user = UserFactory()
    db_session.add(user)
    await db_session.commit()
    return user
```

### FastAPI Test Client
```python
@pytest.fixture
def client(db_session):
    def override_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
```

## Mocking Patterns

### Mock at Boundaries
```python
# Good: Mock external service at infrastructure boundary
@pytest.fixture
def mock_payment_gateway(mocker):
    return mocker.patch(
        "src.infrastructure.payment.StripeGateway.charge",
        return_value=PaymentResult(success=True, transaction_id="txn_123")
    )

# Bad: Mock deep inside domain logic
# This couples tests to implementation details
```

### Repository Mocking
```python
@pytest.fixture
def mock_user_repo():
    repo = Mock(spec=UserRepository)
    repo.get_by_id.return_value = UserFactory(id="123")
    repo.save.side_effect = lambda user: user
    return repo

def test_user_update(mock_user_repo):
    service = UserService(repository=mock_user_repo)
    result = service.update_user("123", {"name": "New Name"})
    
    mock_user_repo.save.assert_called_once()
    assert result.name == "New Name"
```

### Async Mocking
```python
@pytest.fixture
def mock_async_repo(mocker):
    mock = mocker.AsyncMock(spec=UserRepository)
    mock.get_by_id.return_value = UserFactory()
    return mock
```

## Integration Testing

### Database Tests
```python
@pytest.mark.integration
async def test_user_persistence(db_session):
    # Create
    user = User(email="test@example.com", name="Test")
    db_session.add(user)
    await db_session.commit()
    
    # Read
    result = await db_session.get(User, user.id)
    assert result.email == "test@example.com"
    
    # Verify constraints
    duplicate = User(email="test@example.com", name="Duplicate")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
```

### API Integration Tests
```python
@pytest.mark.integration
def test_create_user_endpoint(client, db_session):
    response = client.post(
        "/api/v1/users",
        json={"email": "new@example.com", "name": "New User"}
    )
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == "new@example.com"
    
    # Verify persistence
    user = db_session.query(User).filter_by(id=data["id"]).first()
    assert user is not None
```

### External Service Tests (Contract Testing)
```python
@pytest.mark.integration
@pytest.mark.vcr  # Record/replay HTTP interactions
def test_stripe_payment_integration():
    gateway = StripeGateway(api_key=TEST_API_KEY)
    result = gateway.charge(amount=1000, currency="usd", source="tok_visa")
    
    assert result.success
    assert result.transaction_id.startswith("ch_")
```

## E2E Testing

### Critical Path Only
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_complete_checkout_flow(client, stripe_mock):
    # Create user
    user_response = client.post("/api/v1/users", json={...})
    user_id = user_response.json()["data"]["id"]
    
    # Add to cart
    client.post(f"/api/v1/users/{user_id}/cart", json={"product_id": "prod_1"})
    
    # Checkout
    checkout_response = client.post(
        f"/api/v1/users/{user_id}/checkout",
        json={"payment_method": "pm_card_visa"}
    )
    
    assert checkout_response.status_code == 201
    order = checkout_response.json()["data"]
    assert order["status"] == "confirmed"
```

## Test Markers

### conftest.py
```python
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
```

### pytest.ini
```ini
[pytest]
markers =
    unit: Unit tests
    integration: Integration tests  
    e2e: End-to-end tests
    slow: Slow tests (>1s)
testpaths = tests
asyncio_mode = auto
```

## Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_user_creation():
    service = AsyncUserService()
    user = await service.create({"email": "test@example.com"})
    assert user.id is not None

# Multiple async operations
@pytest.mark.asyncio
async def test_concurrent_operations():
    results = await asyncio.gather(
        service.get_user("1"),
        service.get_user("2"),
        service.get_user("3"),
    )
    assert len(results) == 3
```

## Error Case Testing

```python
def test_user_not_found_raises_exception():
    repo = Mock(spec=UserRepository)
    repo.get_by_id.return_value = None
    service = UserService(repository=repo)
    
    with pytest.raises(UserNotFoundError) as exc_info:
        service.get_user("nonexistent")
    
    assert exc_info.value.user_id == "nonexistent"

def test_validation_error_returns_422(client):
    response = client.post(
        "/api/v1/users",
        json={"email": "not-an-email"}
    )
    
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
```

## Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(st.emails())
def test_email_validation_accepts_valid_emails(email):
    user = User(email=email, name="Test")
    assert user.email == email

@given(st.text(min_size=1, max_size=100))
def test_name_accepts_any_non_empty_string(name):
    user = User(email="test@example.com", name=name)
    assert user.name == name
```

## Test Data Management

### Deterministic IDs
```python
@pytest.fixture(autouse=True)
def deterministic_ids(mocker):
    counter = itertools.count(1)
    mocker.patch("uuid.uuid4", side_effect=lambda: f"test-uuid-{next(counter)}")
```

### Freeze Time
```python
from freezegun import freeze_time

@freeze_time("2024-01-15 12:00:00")
def test_order_expiration():
    order = Order(created_at=datetime.utcnow())
    
    with freeze_time("2024-01-16 12:00:01"):
        assert order.is_expired()
```

## CI/CD Integration

```yaml
# GitHub Actions example
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov
    - name: Run integration tests
      run: pytest tests/integration/ -v
      env:
        DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
```
