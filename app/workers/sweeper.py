"""
Worker for sweeping funds from payment addresses to main wallet.
"""
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.settlement_service import SettlementService
from app.workers.utils import get_enabled_chains
from app.core.logger import logger


async def sweep_funds(ctx):
    """
    ARQ task that sweeps confirmed payments to the main wallet.
    Runs every 30 seconds via cron.
    """
    try:
        logger.info("ARQ task: sweep_funds triggered")
        chains = get_enabled_chains()

        async with async_session() as session:
            settlement_service = SettlementService(session)
            
            for chain_name in chains:
                swept_count = await settlement_service.sweep_chain(chain_name)
                if swept_count > 0:
                    logger.info(f"Swept {swept_count} payments on {chain_name}")

        logger.info("Sweep cycle complete")
        
    except Exception as e:
        logger.error("Error in sweeper: %s", e, exc_info=True)
        raise


async def sweep_specific_address(ctx, address: str, chain_name: str):
    """
    Sweep funds from a specific address.
    Useful for manual operations.
    """
    try:
        logger.info(f"Sweeping address {address} on {chain_name}")
        
        async with async_session() as session:
            settlement_service = SettlementService(session)
            result = await settlement_service.sweep_address(address, chain_name)
            
        logger.info(f"Sweep result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error sweeping address {address}: {e}", exc_info=True)
        raise
