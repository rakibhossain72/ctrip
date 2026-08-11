"""
ARQ cron tasks for payment confirmation and expiry checks.
Detection is handled by the block-polling scanner (scanner/orchestrator.py).
"""
import asyncio

from app.blockchain.chains import chain_id_for_name, load_chains
from app.core.logger import logger
from app.db.async_session import AsyncSessionLocal as async_session
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
                    await confirm_payments(ctx, session, chain_id)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(
                    "Error confirming payments on chain %s: %s", chain_id, e, exc_info=True
                )

        if blockchain is not None:
            await asyncio.gather(*(confirm(c.chain_id) for c in load_chains()))

        async with async_session() as session:
            await check_expired_payments(ctx, session)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in listener cron: %s", e, exc_info=True)
        raise


async def process_single_payment(ctx, payment_id, chain_name: str):  # pylint: disable=unused-argument
    """Manually trigger a confirmation check for a specific payment's chain."""
    try:
        chain_id = chain_id_for_name(chain_name)
        if chain_id is None:
            logger.error("Unknown chain name %r", chain_name)
            return
        logger.info("Processing payment %s on chain %s", payment_id, chain_id)
        async with async_session() as session:
            await confirm_payments(ctx, session, chain_id)
        logger.info("Payment %s processed successfully", payment_id)
    except Exception as e:
        logger.error("Error processing payment %s: %s", payment_id, e, exc_info=True)
        raise
