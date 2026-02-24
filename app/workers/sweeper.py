"""
Worker for sweeping funds from payment addresses to main wallet.
"""
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.blockchain.sweeper import SweeperService
from app.utils.crypto import HDWalletManager
from app.workers.utils import get_enabled_chains
from app.core.logger import logger
from app.core.config import settings


async def sweep_funds(ctx):
    """
    ARQ task that sweeps confirmed payments to the main wallet.
    Runs every 30 seconds via cron.
    """
    try:
        logger.info("="*60)
        logger.info("🧹 ARQ task: sweep_funds triggered")
        logger.info("="*60)
        chains = get_enabled_chains()
        
        hdwallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)

        async with async_session() as session:
            sweeper_service = SweeperService(session, hdwallet)
            
            for chain_name in chains:
                logger.info(f"Sweeping chain: {chain_name}")
                await sweeper_service.sweep_confirmed_payments(chain_name)
                logger.info(f"✅ Sweep completed for {chain_name}")

        logger.info("🧹 Sweep cycle complete")
        logger.info("="*60)
        
    except Exception as e:
        logger.error("❌ Error in sweeper: %s", e, exc_info=True)
        raise


async def sweep_specific_address(ctx, address: str, chain_name: str):
    """
    Sweep funds from a specific address.
    Useful for manual operations.
    
    Note: This is a placeholder for manual sweep operations.
    Implement specific address sweeping logic as needed.
    """
    try:
        logger.info(f"Sweeping address {address} on {chain_name}")
        
        hdwallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)
        
        async with async_session() as session:
            sweeper_service = SweeperService(session, hdwallet)
            # Add specific address sweep logic here
            await sweeper_service.sweep_confirmed_payments(chain_name)
            
        logger.info(f"Sweep completed for address {address}")
        return {"status": "success", "address": address, "chain": chain_name}
        
    except Exception as e:
        logger.error(f"Error sweeping address {address}: {e}", exc_info=True)
        raise
