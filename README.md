# python-testing-patterns

Comprehensive pytest patterns: fixtures, mocking, parametrize, async tests, and API testing. A practical reference for professional Python test suites.

## Quick Start

```bash
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Run excluding slow tests
pytest -m "not slow"

# Verbose with test names
pytest -v

# Stop on first failure
pytest -x
```

## File Overview

| File | Pattern | Description |
|------|---------|-------------|
| `conftest.py` | Fixtures | Shared fixtures — DB, HTTP clients, sample data, mocks |
| `mocking/external_apis.py` | Mocking | Mock HTTP with respx, unittest.mock patterns |
| `parametrize/table_driven.py` | Parametrize | Table-driven tests, indirect parametrize |
| `async_tests/async_patterns.py` | Async | pytest-asyncio, async fixtures, concurrent tests |
| `fixtures/api_client.py` | Fixtures | FastAPI TestClient with auth |
| `test_examples/test_api_endpoints.py` | API testing | Full endpoint test class |

## Fixtures

### Fixture Scopes

```python
@pytest.fixture(scope="function")  # default: fresh per test
@pytest.fixture(scope="class")     # shared within test class
@pytest.fixture(scope="module")    # shared within test file
@pytest.fixture(scope="session")   # shared for entire run
```

### Using Fixtures

```python
# Just declare as parameter — pytest injects automatically
def test_user_creation(sample_user, client, in_memory_db):
    response = client.post("/users", json=sample_user)
    assert response.status_code == 201

# Fixtures can depend on other fixtures
@pytest.fixture
def admin_user(sample_user):
    return {**sample_user, "role": "admin"}
```

### Factory Fixtures (flexible)

```python
@pytest.fixture
def make_user():
    def _make_user(name="Alice", role="user", **kwargs):
        return {"name": name, "role": role, "email": f"{name}@test.com", **kwargs}
    return _make_user

def test_admin_access(make_user):
    admin = make_user(name="Bob", role="admin")
    user = make_user(name="Carol")
```

### autouse Fixtures

```python
@pytest.fixture(autouse=True)  # auto-applied to all tests in scope
def set_test_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
```

## Mocking

### Mock HTTP with respx

```python
import respx, httpx

@respx.mock
def test_api_call():
    respx.get("https://api.example.com/users/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "Alice"})
    )
    result = fetch_user(1)
    assert result["name"] == "Alice"

# As a context manager
with respx.mock:
    respx.post("https://api.example.com/events").mock(
        return_value=httpx.Response(201)
    )
    publish_event({"type": "order.created"})
```

### Mock with unittest.mock

```python
from unittest.mock import patch, MagicMock

# Patch a function
with patch("myapp.services.send_email") as mock_email:
    mock_email.return_value = {"status": "sent"}
    result = register_user("alice@example.com")
    mock_email.assert_called_once_with("alice@example.com", template="welcome")

# Patch an attribute
with patch.object(MyClass, "method_name", return_value="mocked"):
    obj = MyClass()
    assert obj.method_name() == "mocked"

# Side effects
mock.side_effect = [1, 2, ValueError("exhausted")]
```

### monkeypatch (pytest built-in)

```python
def test_env_var(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setattr(mymodule, "MAX_RETRIES", 1)
    monkeypatch.delattr(mymodule, "FEATURE_FLAG", raising=False)
    # All changes auto-reverted after test
```

## Parametrize

```python
@pytest.mark.parametrize("input,expected", [
    ("racecar", True),
    ("hello", False),
    ("A man a plan a canal Panama", True),
])
def test_palindrome(input, expected):
    assert is_palindrome(input) == expected

# Multiple decorators — Cartesian product
@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_multiply(a, b):
    assert a * b == a * b  # runs 4 times

# Indirect — fixture parametrize
@pytest.mark.parametrize("user_fixture,expected", [
    ("admin", True),
    ("regular_user", False),
], indirect=["user_fixture"])
def test_can_delete(user_fixture, expected):
    assert user_fixture.can_delete() == expected
```

## Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_fn()
    assert result == "expected"

# Async fixture
@pytest_asyncio.fixture
async def db_session():
    async with create_async_session() as session:
        yield session
        await session.rollback()

# Concurrent test
@pytest.mark.asyncio
async def test_concurrent():
    results = await asyncio.gather(fetch(1), fetch(2), fetch(3))
    assert len(results) == 3
```

## Test Organization

```
tests/
├── conftest.py          # shared fixtures (auto-loaded)
├── unit/
│   ├── conftest.py      # unit-specific fixtures
│   └── test_*.py
├── integration/
│   ├── conftest.py      # integration fixtures
│   └── test_*.py
└── e2e/
    └── test_*.py
```

## Coverage

```bash
# Run with coverage
pytest --cov=myapp --cov-report=term-missing --cov-report=html

# Minimum coverage threshold (fails if below)
pytest --cov=myapp --cov-fail-under=80

# Coverage configuration in pyproject.toml:
# [tool.coverage.run]
# omit = ["*/tests/*", "*/migrations/*"]
```

## License

MIT
