import asyncio
import logging
from datetime import datetime
import dramatiq
from app.db.async_session import AsyncSessionLocal as async_session
from app.core.config import settings
from app.services.blockchain.scanner import ScannerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIRMATIONS_REQUIRED = 1
BLOCK_BATCH_SIZE = 20

_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

@dramatiq.actor(time_limit=10_000, max_retries=0)
def listen_for_payments():
    try:
        logger.info("Dramatiq actor: listen_for_payments triggered")
        chains = [c["name"] for c in settings.chains]
        if not chains:
            chains = ["anvil"]
            
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

        _loop.run_until_complete(run())
            
        logger.info("Cycle complete - scheduling next run in 5 seconds")
    except Exception as e:
        logger.error(f"Error in listener: {e}", exc_info=True)
    finally:
        listen_for_payments.send_with_options(delay=5000)