"""
Service for sweeping confirmed payments to an admin wallet.
"""
import logging
from eth_account import Account
from sqlalchemy import select, and_
from app.db.models.payment import Payment
from app.core.config import settings

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class SweeperService:
    """
    SweeperService handles moving funds from payment addresses to the admin wallet.
    """
    def __init__(self, session, hd_wallet_manager):
        self.session = session
        self.hd_wallet_manager = hd_wallet_manager

    # pylint: disable=unused-argument
    async def sweep_confirmed_payments(self, chain_name: str):
        """Find and sweep all confirmed payments for a specific chain."""
        logger.info("Starting sweep for chain: %s", chain_name)

        # Get admin wallet address (from mnemonic or private key)
        # pylint: disable=no-value-for-parameter,no-member
        admin_account = Account.from_key(settings.private_key.get_secret_value())
        admin_address = admin_account.address

        # Get confirmed payments that are not yet settled
        payments_res = await self.session.execute(
            select(Payment)
            .where(and_(Payment.status == "confirmed", Payment.chain == chain_name))
        )
        confirmed_payments = list(payments_res.scalars())

        if not confirmed_payments:
            logger.info("No confirmed payments to sweep on %s", chain_name)
            return

        for payment in confirmed_payments:
            try:
                # In a real app, you would:
                # 1. Get private key for payment.address from HD wallet
                # 2. Check balance (Native or Token)
                # 3. If native: send all minus gas to admin_address
                # 4. If token: send native for gas if needed,
                #    then send all tokens to admin_address
                # 5. Mark as "settled"

                logger.info(
                    "Sweeping payment %s from %s to %s",
                    payment.id, payment.address, admin_address
                )

                # Placeholder for actual transaction sending logic
                # For now, just mark as settled
                payment.status = "settled"

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to sweep payment %s: %s", payment.id, e)

        await self.session.commit()
