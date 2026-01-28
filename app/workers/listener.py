"""
Worker for listening to blockchain events and scanning for payments.
"""
import asyncio
import logging
import dramatiq
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.blockchain.scanner import ScannerService
from app.workers.utils import get_enabled_chains

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIRMATIONS_REQUIRED = 1
BLOCK_BATCH_SIZE = 20


@dramatiq.actor(time_limit=10_000, max_retries=0)
def listen_for_payments():
    """
    Dramatiq actor that runs the scanner service to detect new payments.
    """
    try:
        logger.info("Dramatiq actor: listen_for_payments triggered")
        chains = get_enabled_chains()

        async def run():
            async with async_session() as session:
                scanner = ScannerService(
                    session,
                    confirmations_required=CONFIRMATIONS_REQUIRED,
                    block_batch_size=BLOCK_BATCH_SIZE
                )
                for chain_name in chains:
                    await scanner.scan_chain(chain_name)
                    await scanner.confirm_payments(chain_name)

        asyncio.run(run())

        logger.info("Cycle complete - scheduling next run in 5 seconds")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in listener: %s", e, exc_info=True)
    finally:
        listen_for_payments.send_with_options(delay=5000)
