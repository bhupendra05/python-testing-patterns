"""FastAPI TestClient fixtures with authentication support."""
import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.testclient import TestClient


def create_app_with_auth() -> FastAPI:
    """App with JWT-style auth for testing."""
    app = FastAPI()
    security = HTTPBearer()

    VALID_TOKENS = {"admin-token-123": "admin", "user-token-456": "user"}

    def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
        role = VALID_TOKENS.get(creds.credentials)
        if not role:
            raise HTTPException(401, "Invalid token")
        return {"token": creds.credentials, "role": role}

    @app.get("/public")
    def public_endpoint():
        return {"message": "public"}

    @app.get("/protected")
    def protected_endpoint(user=Depends(get_current_user)):
        return {"message": "secret", "role": user["role"]}

    @app.get("/admin")
    def admin_endpoint(user=Depends(get_current_user)):
        if user["role"] != "admin":
            raise HTTPException(403, "Admin only")
        return {"message": "admin area"}

    return app


@pytest.fixture(scope="module")
def auth_app():
    return create_app_with_auth()


@pytest.fixture(scope="module")
def unauth_client(auth_app):
    """Client without any auth headers."""
    return TestClient(auth_app)


@pytest.fixture(scope="module")
def user_client(auth_app):
    return TestClient(auth_app, headers={"Authorization": "Bearer user-token-456"})


@pytest.fixture(scope="module")
def admin_client(auth_app):
    return TestClient(auth_app, headers={"Authorization": "Bearer admin-token-123"})


class TestAuthEndpoints:
    def test_public_no_auth_needed(self, unauth_client):
        r = unauth_client.get("/public")
        assert r.status_code == 200

    def test_protected_requires_auth(self, unauth_client):
        r = unauth_client.get("/protected")
        assert r.status_code == 403  # Missing bearer (HTTPBearer returns 403)

    def test_protected_with_user_token(self, user_client):
        r = user_client.get("/protected")
        assert r.status_code == 200
        assert r.json()["role"] == "user"

    def test_admin_rejects_user(self, user_client):
        r = user_client.get("/admin")
        assert r.status_code == 403

    def test_admin_accepts_admin_token(self, admin_client):
        r = admin_client.get("/admin")
        assert r.status_code == 200
        assert r.json()["message"] == "admin area"
