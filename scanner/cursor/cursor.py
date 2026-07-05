from redis.asyncio import Redis


CURSOR_KEY = "last_scanned_block:{chain_id}"

async def get_cursor(redis: Redis, chain_id: int) -> int | None:
    cursor = await redis.get(CURSOR_KEY.format(chain_id=chain_id))
    return int(cursor) if cursor is not None else None


async def set_cursor(redis: Redis, chain_id: int, block_number: int) -> None:
    await redis.set(CURSOR_KEY.format(chain_id=chain_id), str(block_number))


async def known_cursor_chain_ids(redis: Redis) -> set[int]:
    keys = await redis.keys("last_scanned_block:*")
    return {int(k.decode().split(":")[1]) for k in keys}