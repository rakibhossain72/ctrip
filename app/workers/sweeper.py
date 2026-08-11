"""
Worker for sweeping funds from payment addresses to main wallet.
"""

from app.core.config import settings
from app.core.logger import logger
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.blockchain.sweeper import SweeperService
from app.wallet import WalletKeyManager
from app.workers.utils import get_enabled_chains


async def sweep_funds(ctx):  # pylint: disable=unused-argument
    """
    ARQ task that sweeps confirmed payments to the main wallet.
    Runs every 30 seconds via cron.
    """
    try:
        logger.info("=" * 60)
        logger.info("ARQ task: sweep_funds triggered")
        logger.info("=" * 60)
        chains = get_enabled_chains()

        wallet_manager = WalletKeyManager(
            server_secret_a=settings.wallet_secret_a,
            server_secret_b=settings.wallet_secret_b,
        )

        async with async_session() as session:
            sweeper_service = SweeperService(session, wallet_manager)

            for chain in chains:
                logger.info("Sweeping chain: %s", chain.name)
                await sweeper_service.sweep_confirmed_payments(chain.chain_id)
                logger.info("Sweep completed for %s", chain.name)

        logger.info("Sweep cycle complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("Error in sweeper: %s", e, exc_info=True)
        raise


async def sweep_specific_address(
    ctx, address: str, chain_name: str
):  # pylint: disable=unused-argument
    """
    Sweep funds from a specific address.
    Useful for manual operations.

    Note: This is a placeholder for manual sweep operations.
    Implement specific address sweeping logic as needed.
    """
    try:
        logger.info("Sweeping address %s on %s", address, chain_name)

        from app.blockchain.chains import chain_by_name

        chain = chain_by_name(chain_name)
        if chain is None:
            logger.error("Unknown chain name %r", chain_name)
            return {"status": "error", "address": address, "chain": chain_name}

        wallet_manager = WalletKeyManager(
            server_secret_a=settings.wallet_secret_a,
            server_secret_b=settings.wallet_secret_b,
        )

        async with async_session() as session:
            sweeper_service = SweeperService(session, wallet_manager)
            # Add specific address sweep logic here
            await sweeper_service.sweep_confirmed_payments(chain.chain_id)

        logger.info("Sweep completed for address %s", address)
        return {"status": "success", "address": address, "chain": chain_name}

    except Exception as e:
        logger.error("Error sweeping address %s: %s", address, e, exc_info=True)
        raise
