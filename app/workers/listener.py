"""
Worker for listening to blockchain events and scanning for payments.
"""
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.blockchain.scanner import ScannerService
from app.workers.utils import get_enabled_chains
from app.core.logger import logger

CONFIRMATIONS_REQUIRED = 1
BLOCK_BATCH_SIZE = 20


async def listen_for_payments(ctx):
    """
    ARQ task that runs the scanner service to detect new payments.
    Runs every 5 seconds via cron.
    """
    try:
        logger.info("ARQ task: listen_for_payments triggered")
        chains = get_enabled_chains()

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

        logger.info("Payment scan cycle complete")
        
    except Exception as e:
        logger.error("Error in listener: %s", e, exc_info=True)
        raise  # ARQ will handle retries


async def process_single_payment(ctx, payment_id: int, chain_name: str):
    """
    Process a specific payment by ID.
    Useful for manual reprocessing or webhook triggers.
    """
    try:
        logger.info(f"Processing payment {payment_id} on {chain_name}")
        
        async with async_session() as session:
            scanner = ScannerService(
                session,
                confirmations_required=CONFIRMATIONS_REQUIRED,
                block_batch_size=BLOCK_BATCH_SIZE
            )
            # Add your specific payment processing logic here
            await scanner.confirm_payments(chain_name)
            
        logger.info(f"Payment {payment_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing payment {payment_id}: {e}", exc_info=True)
        raise
