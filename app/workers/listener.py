"""
ARQ cron tasks for payment confirmation and expiry checks.
Detection is handled by ScannerService.start_listeners() (chain-sniper WebSocket).
"""
import asyncio
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.blockchain.scanner import ScannerService
from app.workers.utils import get_enabled_chains
from app.core.logger import logger

CONFIRMATIONS_REQUIRED = 1


async def listen_for_payments(ctx):
    """
    Cron task — confirms detected payments and expires stale ones.
    Block scanning is handled by the always-on ChainSniper listeners.
    """
    try:
        chains = get_enabled_chains()

        async def confirm(chain_name: str):
            try:
                async with async_session() as session:
                    svc = ScannerService(session, confirmations_required=CONFIRMATIONS_REQUIRED)
                    await svc.confirm_payments(chain_name)
            except Exception as e:
                logger.error("Error confirming payments on %s: %s", chain_name, e, exc_info=True)

        if chains:
            await asyncio.gather(*(confirm(c) for c in chains))

        async with async_session() as session:
            svc = ScannerService(session)
            await svc.check_expired_payments()

    except Exception as e:
        logger.error("Error in listener cron: %s", e, exc_info=True)
        raise


async def process_single_payment(ctx, payment_id: int, chain_name: str):
    """Manually trigger a confirmation check for a specific payment."""
    try:
        logger.info("Processing payment %s on %s", payment_id, chain_name)
        async with async_session() as session:
            svc = ScannerService(session, confirmations_required=CONFIRMATIONS_REQUIRED)
            await svc.confirm_payments(chain_name)
        logger.info("Payment %s processed successfully", payment_id)
    except Exception as e:
        logger.error("Error processing payment %s: %s", payment_id, e, exc_info=True)
        raise
