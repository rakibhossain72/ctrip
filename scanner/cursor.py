"""
Redis-backed cursor for tracking the last scanned block per chain.
"""

from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from scanner.constants import CURSOR_KEY


class RedisCursor:
    """Read/write the last-scanned-block cursor for each chain in Redis."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, chain_id: int) -> Optional[int]:
        """Return the last scanned block for *chain_id*, or None."""
        value = await self._redis.get(CURSOR_KEY.format(chain_id=chain_id))
        return int(value) if value is not None else None

    async def set(self, chain_id: int, block_number: int) -> None:
        """Advance the cursor for *chain_id* to *block_number*."""
        await self._redis.set(CURSOR_KEY.format(chain_id=chain_id), str(block_number))

    async def all_chain_ids(self) -> set[int]:
        """Return the set of chain IDs that have a stored cursor."""
        keys = await self._redis.keys(CURSOR_KEY.split("{", maxsplit=1)[0] + "*")
        return {int(key.decode().split(":")[1]) for key in keys}

    async def delete(self, chain_id: int) -> None:
        """Remove the stored cursor for *chain_id*."""
        await self._redis.delete(CURSOR_KEY.format(chain_id=chain_id))
