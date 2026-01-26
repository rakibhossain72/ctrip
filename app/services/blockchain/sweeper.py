import logging
from sqlalchemy import select, and_
from app.blockchain.w3 import get_w3
from app.db.models.payment import Payment
from app.db.models.token import Token
from app.core.config import settings
from eth_account import Account

logger = logging.getLogger(__name__)

class SweeperService:
    def __init__(self, session, hd_wallet_manager):
        self.session = session
        self.hd_wallet_manager = hd_wallet_manager

    async def sweep_confirmed_payments(self, chain_name: str):
        logger.info(f"Starting sweep for chain: {chain_name}")
        w3 = get_w3(chain_name)
        
        # Get admin wallet address (from mnemonic or private key)
        admin_account = Account.from_key(settings.private_key.get_secret_value())
        admin_address = admin_account.address
        
        # Get confirmed payments that are not yet settled
        payments_res = await self.session.execute(
            select(Payment)
            .where(and_(Payment.status == "confirmed", Payment.chain == chain_name))
        )
        confirmed_payments = list(payments_res.scalars())
        
        if not confirmed_payments:
            logger.info(f"No confirmed payments to sweep on {chain_name}")
            return

        for payment in confirmed_payments:
            try:
                # In a real app, you would:
                # 1. Get private key for payment.address from HD wallet
                # 2. Check balance (Native or Token)
                # 3. If native: send all minus gas to admin_address
                # 4. If token: send native for gas if needed, then send all tokens to admin_address
                # 5. Mark as "settled"
                
                logger.info(f"Sweeping payment {payment.id} from {payment.address} to {admin_address}")
                
                # Placeholder for actual transaction sending logic
                # For now, just mark as settled
                payment.status = "settled"
                
            except Exception as e:
                logger.error(f"Failed to sweep payment {payment.id}: {e}")
        
        await self.session.commit()
