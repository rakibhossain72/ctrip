import asyncio
import logging
from datetime import datetime
import dramatiq
from app.db.async_session import AsyncSessionLocal as async_session
from app.core.config import settings
from app.services.blockchain.sweeper import SweeperService
from app.utils.crypto import HDWalletManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Deleted:_loop = asyncio.new_event_loop()
# Deleted:asyncio.set_event_loop(_loop)

@dramatiq.actor(time_limit=10_000, max_retries=0)
def sweep_payments():
    try:
        logger.info("Dramatiq actor: sweep_payments triggered")
        chains = [c["name"] for c in settings.chains]
        if not chains:
            chains = ["anvil"]
            
        async def run():
            async with async_session() as session:
                hd_wallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)
                sweeper = SweeperService(session, hd_wallet)
                for chain_name in chains:
                    await sweeper.sweep_confirmed_payments(chain_name)

        asyncio.run(run())
            
        logger.info("Sweep cycle complete - scheduling next run in 30 seconds")
    except Exception as e:
        logger.error(f"Error in sweeper: {e}", exc_info=True)
    finally:
        sweep_payments.send_with_options(delay=30000)