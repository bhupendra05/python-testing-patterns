"""Example tests showing all patterns on API endpoints.

Uses fixtures from conftest.py (no imports needed for fixtures).
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client: TestClient):
        response = client.get("/health")
        assert response.json()["status"] == "ok"


@pytest.mark.api
class TestUserEndpoints:
    def test_get_existing_user(self, client: TestClient):
        response = client.get("/users/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "name" in data
        assert "email" in data

    def test_get_nonexistent_user_returns_404(self, client: TestClient):
        response = client.get("/users/404")
        assert response.status_code == 404

    def test_create_user(self, client: TestClient, sample_user):
        response = client.post("/users", json={
            "name": sample_user["name"],
            "email": sample_user["email"],
        })
        assert response.status_code == 200
        assert response.json()["email"] == sample_user["email"]

    @pytest.mark.parametrize("user_id,expected_status", [
        (1, 200),
        (42, 200),
        (404, 404),
    ])
    def test_get_user_parametrized(self, client: TestClient, user_id: int, expected_status: int):
        response = client.get(f"/users/{user_id}")
        assert response.status_code == expected_status
