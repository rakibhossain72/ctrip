"""
Worker for listening to blockchain events and scanning for payments.
"""
import dramatiq
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.blockchain.scanner import ScannerService
from app.workers.utils import get_enabled_chains
from app.workers.async_utils import run_async


from app.core.logger import logger

CONFIRMATIONS_REQUIRED = 1
BLOCK_BATCH_SIZE = 20


@dramatiq.actor(time_limit=600_000, max_retries=0)
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
                # Check for expired payments across all chains
                await scanner.check_expired_payments()

        run_async(run())

        logger.info("Cycle complete - scheduling next run in 5 seconds")
    except BaseException as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in listener: %s", e, exc_info=True)
        if isinstance(e, SystemExit):
            raise
    finally:
        listen_for_payments.send_with_options(delay=5000)
