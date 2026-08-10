"""
ARQ cron tasks for payment confirmation and expiry checks.
Detection is handled by the block-polling scanner (scanner/orchestrator.py).
"""
import asyncio

from app.blockchain.chains import load_chains
from app.db.async_session import AsyncSessionLocal as async_session
from app.core.logger import logger
from scanner.lifecycle import check_expired_payments, confirm_payments


async def listen_for_payments(ctx):  # pylint: disable=unused-argument
    """
    Cron task — confirms detected payments and expires stale ones.
    """
    blockchain = ctx.get("blockchain_service")

    try:
        async def confirm(chain_id: int):
            try:
                async with async_session() as session:
                    await confirm_payments(session, blockchain, chain_id)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(
                    "Error confirming payments on chain %s: %s", chain_id, e, exc_info=True
                )

        if blockchain is not None:
            await asyncio.gather(*(confirm(c.chain_id) for c in load_chains()))

        async with async_session() as session:
            await check_expired_payments(session)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in listener cron: %s", e, exc_info=True)
        raise


async def process_single_payment(ctx, payment_id: int, chain_id: int):  # pylint: disable=unused-argument
    """Manually trigger a confirmation check for a specific chain."""
    try:
        logger.info("Processing payment %s on chain %s", payment_id, chain_id)
        blockchain = ctx.get("blockchain_service")
        async with async_session() as session:
            await confirm_payments(session, blockchain, chain_id)
        logger.info("Payment %s processed successfully", payment_id)
    except Exception as e:
        logger.error("Error processing payment %s: %s", payment_id, e, exc_info=True)
        raise
