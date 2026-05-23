"""Root conftest.py — shared fixtures for all tests.

conftest.py is auto-loaded by pytest. Fixtures defined here
are available to all tests without importing.

Fixture scopes:
- function (default): fresh fixture per test
- class: shared within a test class
- module: shared within a test file
- session: shared across entire test run

Best practices:
- Keep fixtures small and focused
- Use factory fixtures for flexibility
- Prefer session scope for expensive setup (DB connections)
- Use function scope for state that mutates between tests
"""
import asyncio
import json
import os
from typing import Dict, Any, Generator
from unittest.mock import MagicMock, patch

import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────── Event Loop (async) ────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async tests.

    Without this, pytest-asyncio creates a new loop per test,
    which can cause issues with async database connections.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ─────────────────────────── Database ──────────────────────────────────

@pytest.fixture(scope="function")
def in_memory_db():
    """In-memory SQLite database — fresh per test.

    Returns a dict-based fake DB for simplicity.
    In real projects, use SQLAlchemy with create_engine("sqlite:///:memory:")
    """
    db = {
        "users": {},
        "orders": {},
        "products": {},
    }
    return db


@pytest.fixture(scope="session")
def db_config() -> Dict[str, str]:
    """Database configuration for tests."""
    return {
        "url": os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:"),
        "pool_size": "5",
        "echo": "false",
    }


# ─────────────────────────── FastAPI / HTTP Client ─────────────────────

def create_test_app() -> FastAPI:
    """Create a minimal FastAPI app for testing."""
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        if user_id == 404:
            from fastapi import HTTPException
            raise HTTPException(404, "Not found")
        return {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@test.com"}

    @app.post("/users")
    def create_user(body: dict):
        return {"id": 1, **body}

    return app


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """FastAPI app instance (module-scoped for performance)."""
    return create_test_app()


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    """FastAPI TestClient — synchronous HTTP client for testing.

    Module-scoped so the app is created once per test file.
    """
    return TestClient(app)


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """TestClient with pre-set auth headers."""
    client.headers.update({"Authorization": "Bearer test-token-12345"})
    yield client
    # Cleanup auth header after test
    client.headers.pop("Authorization", None)


@pytest.fixture
async def async_client(app: FastAPI):
    """Async HTTP client for async endpoint tests."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ─────────────────────────── Sample Data ───────────────────────────────

@pytest.fixture
def sample_user() -> Dict[str, Any]:
    """A valid user dict for use in tests."""
    return {
        "id": 1,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "role": "user",
        "is_active": True,
    }


@pytest.fixture
def sample_users() -> list:
    """List of sample users."""
    return [
        {"id": i, "name": f"User {i}", "email": f"user{i}@example.com", "role": "user"}
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_product() -> Dict[str, Any]:
    return {
        "id": 1,
        "name": "Mechanical Keyboard",
        "price": 129.99,
        "stock": 50,
        "category": "Electronics",
    }


@pytest.fixture
def sample_order(sample_user, sample_product) -> Dict[str, Any]:
    return {
        "id": 1,
        "customer": sample_user,
        "items": [{"product": sample_product, "quantity": 2}],
        "total": sample_product["price"] * 2,
        "status": "pending",
    }


# ─────────────────────────── External Service Mocks ────────────────────

@pytest.fixture
def mock_email_service():
    """Mock email service — captures sent emails."""
    with patch("smtplib.SMTP") as mock_smtp:
        sent_emails = []

        def fake_send(from_addr, to_addrs, msg):
            sent_emails.append({"from": from_addr, "to": to_addrs, "msg": msg})

        mock_smtp.return_value.__enter__.return_value.sendmail = fake_send
        yield {"mock": mock_smtp, "sent": sent_emails}


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None  # cache miss by default
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_s3():
    """Mock AWS S3 client."""
    mock = MagicMock()
    mock.upload_file.return_value = None
    mock.download_file.return_value = None
    mock.generate_presigned_url.return_value = "https://example.s3.amazonaws.com/file.jpg?sig=..."
    return mock


# ─────────────────────────── Environment ───────────────────────────────

@pytest.fixture(autouse=True)
def set_test_environment(monkeypatch):
    """Auto-use: ensure test env vars are set for every test."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-minimum-32-characters-long")


@pytest.fixture
def temp_file(tmp_path):
    """Temporary file that's cleaned up after the test."""
    file = tmp_path / "test_output.json"
    yield file
    # tmp_path is automatically cleaned up by pytest


# ─────────────────────────── Pytest Config ─────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with -m 'not slow')")
    config.addinivalue_line("markers", "integration: marks integration tests requiring external services")
    config.addinivalue_line("markers", "unit: marks pure unit tests")
    config.addinivalue_line("markers", "api: marks API endpoint tests")
