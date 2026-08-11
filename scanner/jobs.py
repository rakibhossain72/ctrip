from __future__ import annotations

import logging

from app.db.models import PaymentEventType
from scanner.db_service.events import record_event
from scanner.db_service.payments import (
    get_pending_erc20,
    get_pending_native,
    mark_detected,
)
from scanner.matching import (
    _to_hex_str,
    decode_erc20_transfer,
    match_native_tx,
    normalize_address,
)

logger = logging.getLogger("scanner.jobs")


def _tx_hash(tx: dict) -> str:
    return _to_hex_str(tx.get("hash")) or ""


async def check_native_transactions(ctx, chain_id: int, blocks: list[int]) -> None:
    """Fetch each unscanned block's transactions and enqueue a per-block job."""
    blockchain = ctx["blockchain_service"]
    arq_pool = ctx["arq_pool"]

    for block_number in blocks:
        try:
            transactions = await blockchain.get_block_transactions(
                chain_id, block_number
            )
        except Exception:
            logger.exception(
                "Failed to fetch block %s on chain %s", block_number, chain_id
            )
            continue
        if transactions:
            await arq_pool.enqueue_job(
                "process_block", chain_id, block_number, transactions
            )


async def process_block(
    ctx, chain_id: int, block_number: int, transactions: list
) -> None:
    """Match native-currency transactions against pending payments."""
    db_factory = ctx["db_factory"]
    async with db_factory() as db:
        watched = await get_pending_native(db, chain_id)
        if not watched:
            return

        watched_keys = set(watched)
        detected = 0
        for tx in transactions:
            matched = match_native_tx(tx, watched_keys)
            if not matched:
                continue
            payment = watched[matched]
            value = int(tx.get("value") or 0)
            if value < payment.amount_raw:
                continue
            recorded = await record_event(
                db,
                payment_id=payment.id,
                chain_id=chain_id,
                event_type=PaymentEventType.NATIVE,
                tx_hash=_tx_hash(tx),
                block_number=block_number,
                value_raw=value,
                from_address=normalize_address(tx.get("from") or ""),
                to_address=matched,
            )
            if recorded and await mark_detected(db, payment.id, block_number):
                detected += 1

        await db.commit()
        if detected:
            logger.info(
                "chain %s block %s detected %d native payment(s)",
                chain_id,
                block_number,
                detected,
            )


async def check_erc20_transfer_logs(
    ctx, chain_id: int, token: str, from_block: int, to_block: int
) -> None:
    """Fetch ERC-20 Transfer logs for a token over a block range."""
    db_factory = ctx["db_factory"]
    async with db_factory() as db:
        watched = await get_pending_erc20(db, chain_id, token)
    if not watched:
        return

    blockchain = ctx["blockchain_service"]
    try:
        logs = await blockchain.get_transfer_logs(
            chain_id,
            from_block=from_block,
            to_block=to_block,
            token_addresses=[token],
            to_addresses=list(watched),
        )
    except Exception:
        logger.exception(
            "Failed to fetch transfer logs for token %s chain %s", token, chain_id
        )
        return

    if logs:
        await ctx["arq_pool"].enqueue_job("process_log", chain_id, token, logs)


async def process_log(ctx, chain_id: int, token: str, logs: list) -> None:
    """Match decoded ERC-20 Transfer logs against pending payments."""
    db_factory = ctx["db_factory"]
    async with db_factory() as db:
        watched = await get_pending_erc20(db, chain_id, token)
        if not watched:
            return

        detected = 0
        for log in logs:
            event = decode_erc20_transfer(log, chain_id)
            if event is None or event.token != token.lower():
                continue
            payment = watched.get(event.to)
            if payment is None:
                continue
            if event.amount < payment.amount_raw:
                continue
            recorded = await record_event(
                db,
                payment_id=payment.id,
                chain_id=chain_id,
                event_type=PaymentEventType.ERC20,
                tx_hash=event.tx_hash,
                block_number=event.block_number or 0,
                value_raw=event.amount,
                token_contract=event.token,
                log_index=event.log_index,
                from_address=event.from_ or "",
                to_address=event.to,
            )
            if recorded and await mark_detected(
                db, payment.id, event.block_number or 0
            ):
                detected += 1

        await db.commit()
        if detected:
            logger.info(
                "chain %s token %s detected %d ERC-20 payment(s)",
                chain_id,
                token,
                detected,
            )
