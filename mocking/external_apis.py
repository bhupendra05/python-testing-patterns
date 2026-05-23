"""Mocking external APIs with respx (httpx) and unittest.mock.

Patterns:
- Mock HTTP calls with respx (httpx-based)
- Mock AWS with moto (boto3)
- Mock time and random
- Mock file system with tmp_path
- Spy on function calls
"""
import json
import time
import httpx
import pytest
import respx
from unittest.mock import patch, MagicMock, call


# ─────────────────────────── Functions Under Test ──────────────────────

def fetch_github_user(username: str) -> dict:
    """Fetch GitHub user profile."""
    response = httpx.get(f"https://api.github.com/users/{username}")
    response.raise_for_status()
    return response.json()


def fetch_weather(city: str, api_key: str) -> dict:
    """Fetch weather data from OpenWeatherMap."""
    url = f"https://api.openweathermap.org/data/2.5/weather"
    response = httpx.get(url, params={"q": city, "appid": api_key})
    if response.status_code == 404:
        raise ValueError(f"City '{city}' not found")
    response.raise_for_status()
    return response.json()


def send_slack_notification(webhook_url: str, message: str) -> bool:
    """Send a Slack webhook notification."""
    response = httpx.post(webhook_url, json={"text": message})
    return response.status_code == 200


# ─────────────────────────── respx Tests ───────────────────────────────

class TestGitHubAPI:
    """Test GitHub API calls using respx mocking."""

    @respx.mock
    def test_fetch_user_success(self):
        """Mock successful GitHub user fetch."""
        # Arrange: set up mock
        respx.get("https://api.github.com/users/octocat").mock(
            return_value=httpx.Response(
                200,
                json={
                    "login": "octocat",
                    "name": "The Octocat",
                    "public_repos": 8,
                    "followers": 5000,
                },
            )
        )

        # Act
        result = fetch_github_user("octocat")

        # Assert
        assert result["login"] == "octocat"
        assert result["name"] == "The Octocat"
        assert result["public_repos"] == 8

    @respx.mock
    def test_fetch_user_not_found(self):
        """Mock 404 response."""
        respx.get("https://api.github.com/users/nonexistent").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetch_github_user("nonexistent")
        assert exc_info.value.response.status_code == 404

    @respx.mock
    def test_fetch_user_network_error(self):
        """Mock network timeout."""
        respx.get("https://api.github.com/users/timeout-user").mock(
            side_effect=httpx.ConnectTimeout("Connection timed out")
        )

        with pytest.raises(httpx.ConnectTimeout):
            fetch_github_user("timeout-user")

    @respx.mock
    def test_weather_city_not_found(self):
        """Mock 404 from weather API."""
        respx.get("https://api.openweathermap.org/data/2.5/weather").mock(
            return_value=httpx.Response(404, json={"message": "city not found"})
        )

        with pytest.raises(ValueError, match="not found"):
            fetch_weather("InvalidCity", api_key="test-key")

    @respx.mock
    def test_slack_notification(self):
        """Mock Slack webhook."""
        webhook_url = "https://hooks.slack.com/services/T00/B00/xxx"
        respx.post(webhook_url).mock(return_value=httpx.Response(200))

        result = send_slack_notification(webhook_url, "Deployment complete!")
        assert result is True

    @respx.mock
    def test_slack_notification_failure(self):
        """Mock Slack webhook failure."""
        webhook_url = "https://hooks.slack.com/services/T00/B00/xxx"
        respx.post(webhook_url).mock(return_value=httpx.Response(429))

        result = send_slack_notification(webhook_url, "Test")
        assert result is False


# ─────────────────────────── unittest.mock Tests ────────────────────────

class TestMockingPatterns:
    """Various unittest.mock patterns."""

    def test_patch_method(self):
        """Patch a single method on a class."""
        with patch("httpx.get") as mock_get:
            mock_get.return_value.json.return_value = {"key": "value"}
            mock_get.return_value.status_code = 200

            response = httpx.get("https://example.com")
            assert response.json() == {"key": "value"}
            mock_get.assert_called_once_with("https://example.com")

    def test_mock_with_side_effect_list(self):
        """Return different values on successive calls."""
        mock_fn = MagicMock()
        mock_fn.side_effect = [1, 2, 3, ValueError("exhausted")]

        assert mock_fn() == 1
        assert mock_fn() == 2
        assert mock_fn() == 3
        with pytest.raises(ValueError):
            mock_fn()

    def test_mock_call_assertions(self):
        """Verify mock was called with specific arguments."""
        mock_send = MagicMock()

        # Simulate calling send with different args
        mock_send("alice@example.com", subject="Welcome")
        mock_send("bob@example.com", subject="Invoice")

        assert mock_send.call_count == 2
        mock_send.assert_called_with("bob@example.com", subject="Invoice")
        assert call("alice@example.com", subject="Welcome") in mock_send.call_args_list

    def test_patch_time(self):
        """Mock time.time() for deterministic timestamps."""
        with patch("time.time", return_value=1700000000.0):
            ts = time.time()
        assert ts == 1700000000.0

    def test_spy_pattern(self):
        """Spy: call real function AND record calls."""
        real_list = []
        original_append = list.append

        with patch.object(list, "append", wraps=original_append) as spy:
            real_list.append(1)
            real_list.append(2)

        assert real_list == [1, 2]  # real function was called
        assert spy.call_count == 2  # AND we recorded the calls

    def test_context_manager_mock(self):
        """Mock a context manager (__enter__/__exit__)."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = '{"key": "value"}'

        with patch("builtins.open", return_value=mock_file):
            with open("config.json") as f:
                data = json.loads(f.read())

        assert data["key"] == "value"

    def test_patch_environment_variable(self, monkeypatch):
        """Use pytest monkeypatch for env vars (cleaner than os.environ)."""
        monkeypatch.setenv("API_KEY", "test-api-key-12345")
        import os
        assert os.environ["API_KEY"] == "test-api-key-12345"
        # Auto-restored after test

    def test_tmp_file_fixture(self, tmp_path):
        """Use tmp_path for file-system tests."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"users": [1, 2, 3]}))

        content = json.loads(test_file.read_text())
        assert content["users"] == [1, 2, 3]
        # tmp_path auto-cleaned by pytest


# ─────────────────────────── pytest fixtures as mocks ──────────────────

@pytest.fixture
def mock_github_api():
    """Reusable fixture for GitHub API mocking."""
    with respx.mock(base_url="https://api.github.com") as respx_mock:
        respx_mock.get("/users/octocat").mock(
            return_value=httpx.Response(
                200,
                json={"login": "octocat", "name": "The Octocat", "public_repos": 8},
            )
        )
        respx_mock.get("/users/nonexistent").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        yield respx_mock


def test_fetch_github_user_with_fixture(mock_github_api):
    """Use the mock_github_api fixture."""
    result = fetch_github_user("octocat")
    assert result["login"] == "octocat"


def test_github_404_with_fixture(mock_github_api):
    """Test 404 using the same fixture."""
    with pytest.raises(httpx.HTTPStatusError):
        fetch_github_user("nonexistent")
