"""Unit tests for scanner/cursor.py using an in-memory Redis stub."""

import pytest

from scanner.cursor import RedisCursor


class FakeRedis:
    """Tiny in-memory stand-in for the redis.asyncio client."""

    def __init__(self):
        self._data: dict[str, str] = {}

    async def get(self, key: str):
        """Return the value for a key, or None."""
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        """Store a value for a key."""
        self._data[key] = value

    async def keys(self, pattern: str) -> list[bytes]:
        """Return keys matching a glob pattern."""
        prefix = pattern.split("*")[0]
        return [k.encode() for k in self._data if k.startswith(prefix)]

    async def delete(self, key: str) -> None:
        """Delete a key."""
        self._data.pop(key, None)


@pytest.fixture
async def _cursor():
    return RedisCursor(FakeRedis())


async def test_get_missing_returns_none(_cursor: RedisCursor):
    """A missing key should return None."""
    assert await _cursor.get(1) is None


async def test_set_and_get_roundtrip(_cursor: RedisCursor):
    """Set then get should return the same block number."""
    await _cursor.set(11155111, 12345)
    assert await _cursor.get(11155111) == 12345


async def test_all_chain_ids(_cursor: RedisCursor):
    """all_chain_ids should return every chain that has a cursor."""
    await _cursor.set(1, 100)
    await _cursor.set(56, 200)
    assert await _cursor.all_chain_ids() == {1, 56}


async def test_delete(_cursor: RedisCursor):
    """Deleting a key should remove it from Redis."""
    await _cursor.set(1, 100)
    await _cursor.delete(1)
    assert await _cursor.get(1) is None
    assert await _cursor.all_chain_ids() == set()
