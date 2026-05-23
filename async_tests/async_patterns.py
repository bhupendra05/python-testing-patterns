"""pytest-asyncio patterns — async test functions, fixtures, and context managers.

Requirements:
    pip install pytest-asyncio

Configuration (pytest.ini or pyproject.toml):
    [pytest]
    asyncio_mode = auto  # auto-discover async tests
"""
import asyncio
from typing import AsyncGenerator, List
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio


# ─────────────────────────── Async Functions Under Test ────────────────

async def fetch_data(url: str) -> dict:
    """Async HTTP fetch."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def process_items_concurrently(items: List[int]) -> List[int]:
    """Process items concurrently using asyncio.gather."""
    async def process_one(item: int) -> int:
        await asyncio.sleep(0.01)  # simulate I/O
        return item * 2

    results = await asyncio.gather(*[process_one(item) for item in items])
    return list(results)


async def read_with_timeout(delay: float, timeout: float = 1.0) -> str:
    """Operation with timeout."""
    async def slow_operation():
        await asyncio.sleep(delay)
        return "done"

    return await asyncio.wait_for(slow_operation(), timeout=timeout)


class AsyncRepository:
    """Simulated async database repository."""

    def __init__(self):
        self._data = {}

    async def save(self, key: str, value: dict) -> dict:
        await asyncio.sleep(0.01)  # simulate DB write
        self._data[key] = value
        return value

    async def find(self, key: str) -> dict | None:
        await asyncio.sleep(0.01)  # simulate DB read
        return self._data.get(key)

    async def find_all(self) -> List[dict]:
        await asyncio.sleep(0.01)
        return list(self._data.values())

    async def delete(self, key: str) -> bool:
        await asyncio.sleep(0.01)
        return bool(self._data.pop(key, None))


# ─────────────────────────── Async Fixtures ────────────────────────────

@pytest_asyncio.fixture
async def async_repo() -> AsyncGenerator[AsyncRepository, None]:
    """Async fixture — repository with test data pre-loaded."""
    repo = AsyncRepository()
    # Setup: add test data
    await repo.save("user:1", {"id": 1, "name": "Alice", "email": "alice@test.com"})
    await repo.save("user:2", {"id": 2, "name": "Bob", "email": "bob@test.com"})
    yield repo
    # Teardown: (in real app, close DB connections, rollback transactions)


@pytest_asyncio.fixture
async def mock_http_client():
    """Async fixture providing a mocked httpx client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get.return_value.json.return_value = {"mocked": True}
    mock_client.get.return_value.status_code = 200
    return mock_client


# ─────────────────────────── Async Tests ───────────────────────────────

@pytest.mark.asyncio
async def test_process_items_concurrently():
    """Test concurrent processing."""
    items = [1, 2, 3, 4, 5]
    results = await process_items_concurrently(items)
    assert results == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_process_concurrency_is_fast():
    """Verify concurrent processing is faster than sequential."""
    items = list(range(20))

    start = asyncio.get_event_loop().time()
    results = await process_items_concurrently(items)
    elapsed = asyncio.get_event_loop().time() - start

    # Sequential would take 20 * 0.01 = 0.2s
    # Concurrent should be ~0.01s
    assert elapsed < 0.1, f"Expected < 0.1s but took {elapsed:.3f}s"
    assert len(results) == 20


@pytest.mark.asyncio
async def test_timeout_completes_in_time():
    """Test operation that completes before timeout."""
    result = await read_with_timeout(delay=0.05, timeout=1.0)
    assert result == "done"


@pytest.mark.asyncio
async def test_timeout_raises_on_slow_operation():
    """Test operation that exceeds timeout."""
    with pytest.raises(asyncio.TimeoutError):
        await read_with_timeout(delay=2.0, timeout=0.1)


@pytest.mark.asyncio
async def test_async_repo_save_and_find(async_repo: AsyncRepository):
    """Test async repository operations using async fixture."""
    # Data pre-loaded by fixture
    alice = await async_repo.find("user:1")
    assert alice is not None
    assert alice["name"] == "Alice"

    # Add new data
    new_user = await async_repo.save("user:3", {"id": 3, "name": "Carol"})
    assert new_user["name"] == "Carol"

    # Verify it's findable
    found = await async_repo.find("user:3")
    assert found["name"] == "Carol"


@pytest.mark.asyncio
async def test_async_repo_delete(async_repo: AsyncRepository):
    """Test async delete."""
    deleted = await async_repo.delete("user:1")
    assert deleted is True

    result = await async_repo.find("user:1")
    assert result is None


@pytest.mark.asyncio
async def test_async_repo_find_all(async_repo: AsyncRepository):
    """Test async find_all."""
    all_users = await async_repo.find_all()
    assert len(all_users) == 2  # fixture loaded 2 users


@pytest.mark.asyncio
async def test_concurrent_repo_operations(async_repo: AsyncRepository):
    """Test many concurrent DB operations."""
    # Simulate 10 concurrent saves
    tasks = [
        async_repo.save(f"item:{i}", {"id": i, "value": i * 10})
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10

    # All should be retrievable
    all_items = await async_repo.find_all()
    assert len(all_items) == 12  # 2 from fixture + 10 new


@pytest.mark.asyncio
async def test_mock_async_http():
    """Test async function with mocked HTTP client."""
    mock_response = AsyncMock()
    mock_response.json.return_value = {"user": "octocat", "repos": 8}
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await fetch_data("https://api.github.com/users/octocat")

    assert result["user"] == "octocat"
    mock_client.get.assert_called_once_with("https://api.github.com/users/octocat")
