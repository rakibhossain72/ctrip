"""
Worker for sweeping confirmed payments and settling them.
"""
import asyncio
import dramatiq
from app.db.async_session import AsyncSessionLocal as async_session
from app.core.config import settings
from app.services.blockchain.sweeper import SweeperService
from app.utils.crypto import HDWalletManager
from app.workers.utils import get_enabled_chains

from app.core.logger import logger


@dramatiq.actor(time_limit=10_000, max_retries=0)
def sweep_payments():
    """
    Dramatiq actor that runs the sweeper service to process confirmed payments.
    """
    try:
        logger.info("Dramatiq actor: sweep_payments triggered")
        chains = get_enabled_chains()

        async def run():
            async with async_session() as session:
                hd_wallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)
                sweeper = SweeperService(session, hd_wallet)
                for chain_name in chains:
                    await sweeper.sweep_confirmed_payments(chain_name)

        asyncio.run(run())

        logger.info("Sweep cycle complete - scheduling next run in 30 seconds")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in sweeper: %s", e, exc_info=True)
    finally:
        sweep_payments.send_with_options(delay=30000)
