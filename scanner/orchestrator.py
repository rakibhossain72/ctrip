from __future__ import annotations

import asyncio
import logging

from app.db.async_session import AsyncSessionLocal
from scanner.constants import MAX_BLOCKS_PER_TICK
from scanner.db_service.payments import active_scan_targets

logger = logging.getLogger("scanner.orchestrator")


async def _scan_chain(ctx, chain_id: int, spec: dict) -> None:
    cursor = ctx["cursor"]
    blockchain = ctx["blockchain_service"]
    arq_pool = ctx["arq_pool"]

    try:
        current_block = await blockchain.get_current_block(chain_id)
    except Exception:
        logger.exception("Failed to get current block for chain %s", chain_id)
        return

    last_scanned = await cursor.get(chain_id)
    if last_scanned is None:
        # First time we've seen this chain — seed the cursor, no backfill.
        await cursor.set(chain_id, current_block - 1)
        logger.info(
            "seeded cursor for chain %s at block %s", chain_id, current_block - 1
        )
        return

    if current_block <= last_scanned:
        return

    to_block = min(current_block, last_scanned + MAX_BLOCKS_PER_TICK)
    blocks = list(range(last_scanned + 1, to_block + 1))

    if spec["native"]:
        await arq_pool.enqueue_job("check_native_transactions", chain_id, blocks)

    for token in spec["tokens"]:
        await arq_pool.enqueue_job(
            "check_erc20_transfer_logs", chain_id, token, blocks[0], blocks[-1]
        )

    # Cursor advances once tasks are enqueued, not once they complete (see
    # block-scanning-implementation.md) — bounded ranges + arq retries mitigate gaps.
    await cursor.set(chain_id, to_block)
    logger.info(
        "chain %s queued blocks %s..%s (native=%s tokens=%d)",
        chain_id,
        blocks[0],
        blocks[-1],
        spec["native"],
        len(spec["tokens"]),
    )


async def scan_orchestrator(ctx) -> None:
    """Cron entrypoint (every 10s): scan every chain with active payments."""
    async with AsyncSessionLocal() as db:
        targets = await active_scan_targets(db)

    if not targets:
        return

    await asyncio.gather(
        *(_scan_chain(ctx, cid, spec) for cid, spec in targets.items())
    )


async def prune_stale_cursors(ctx) -> None:
    """Hourly cron: drop cursors for chains with no configured payments."""
    cursor = ctx["cursor"]
    async with AsyncSessionLocal() as db:
        targets = await active_scan_targets(db)

    tracked = await cursor.all_chain_ids()
    for chain_id in tracked - set(targets):
        await cursor.delete(chain_id)
        logger.info("dropped cursor for inactive chain %s", chain_id)


async def backfill_chain(ctx, chain_id: int, from_block: int, to_block: int) -> None:
    """Explicitly enqueue scanning for a historical block range."""
    arq_pool = ctx["arq_pool"]
    blocks = list(range(from_block, to_block + 1))

    async with AsyncSessionLocal() as db:
        spec = (await active_scan_targets(db)).get(
            chain_id, {"native": False, "tokens": set()}
        )

    if not blocks or (not spec["native"] and not spec["tokens"]):
        return

    if spec["native"]:
        await arq_pool.enqueue_job("check_native_transactions", chain_id, blocks)
    for token in spec["tokens"]:
        await arq_pool.enqueue_job(
            "check_erc20_transfer_logs", chain_id, token, blocks[0], blocks[-1]
        )
    await ctx["cursor"].set(chain_id, to_block)
