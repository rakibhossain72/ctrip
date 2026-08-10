"""Unit tests for scanner/cursor.py using an in-memory Redis stub."""

import pytest

from scanner.cursor import RedisCursor


class FakeRedis:
    """Tiny in-memory stand-in for the redis.asyncio client."""

    def __init__(self):
        self._data: dict[str, str] = {}

    async def get(self, key: str):
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value

    async def keys(self, pattern: str) -> list[bytes]:
        prefix = pattern.split("*")[0]
        return [k.encode() for k in self._data if k.startswith(prefix)]

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


@pytest.fixture
async def cursor():
    return RedisCursor(FakeRedis())


async def test_get_missing_returns_none(cursor: RedisCursor):
    assert await cursor.get(1) is None


async def test_set_and_get_roundtrip(cursor: RedisCursor):
    await cursor.set(11155111, 12345)
    assert await cursor.get(11155111) == 12345


async def test_all_chain_ids(cursor: RedisCursor):
    await cursor.set(1, 100)
    await cursor.set(56, 200)
    assert await cursor.all_chain_ids() == {1, 56}


async def test_delete(cursor: RedisCursor):
    await cursor.set(1, 100)
    await cursor.delete(1)
    assert await cursor.get(1) is None
    assert await cursor.all_chain_ids() == set()
