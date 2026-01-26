import logging
from sqlalchemy import select, and_
from app.blockchain.w3 import get_w3
from app.db.models.payment import Payment
from app.db.models.chain import ChainState
from app.db.models.token import Token
from app.workers.webhook import send_webhook_task
from app.core.config import settings

logger = logging.getLogger(__name__)

ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

class ScannerService:
    def __init__(self, session, confirmations_required=1, block_batch_size=20):
        self.session = session
        self.confirmations_required = confirmations_required
        self.block_batch_size = block_batch_size

    async def scan_chain(self, chain_name: str):
        logger.info(f"Scanning chain: {chain_name}")
        w3 = get_w3(chain_name)
        
        state_res = await self.session.execute(
            select(ChainState)
            .where(ChainState.chain == chain_name)
            .with_for_update()
        )
        state = state_res.scalar_one_or_none()
        if not state:
            logger.warning(f"No chain state found for {chain_name}, skipping")
            return

        latest_block = await w3.eth.block_number
        from_block = state.last_scanned_block + 1
        to_block = min(from_block + self.block_batch_size, latest_block)
        
        if from_block > to_block:
            return
        
        payments_res = await self.session.execute(
            select(Payment)
            .where(and_(Payment.status == "pending", Payment.chain == chain_name))
        )
        payment_list = list(payments_res.scalars())
        
        if not payment_list:
            state.last_scanned_block = to_block
            await self.session.commit()
            return

        native_payments = {p.address.lower(): p for p in payment_list if p.token_id is None}
        erc20_payments = {p.address.lower(): p for p in payment_list if p.token_id is not None}
        
        detected_count = 0
        for block_number in range(from_block, to_block + 1):
            block = await w3.eth.get_block(block_number, full_transactions=True)
            
            # Native transfers
            for tx in block.transactions:
                if not tx.to: continue
                addr = tx.to.lower()
                if addr in native_payments:
                    payment = native_payments[addr]
                    if tx.value >= payment.amount:
                        logger.info(f"Native Payment detected! ID: {payment.id}")
                        payment.status = "detected"
                        payment.detected_in_block = block_number
                        detected_count += 1
            
            # ERC20 transfers
            if erc20_payments:
                logs = await w3.eth.get_logs({
                    "fromBlock": block_number,
                    "toBlock": block_number,
                    "topics": [ERC20_TRANSFER_TOPIC]
                })
                for log in logs:
                    if len(log.topics) < 3: continue
                    to_address = "0x" + log.topics[2].hex()[-40:].lower()
                    if to_address in erc20_payments:
                        payment = erc20_payments[to_address]
                        token_res = await self.session.execute(select(Token).where(Token.id == payment.token_id))
                        token = token_res.scalar_one_or_none()
                        if token and log.address.lower() == token.address.lower():
                            value = int(log.data.hex(), 16) if log.data else 0
                            if value >= payment.amount:
                                logger.info(f"ERC20 Payment detected! ID: {payment.id}")
                                payment.status = "detected"
                                payment.detected_in_block = block_number
                                detected_count += 1
        
        state.last_scanned_block = to_block
        await self.session.commit()
        logger.info(f"Scan complete for {chain_name}. Detected: {detected_count}")

    async def confirm_payments(self, chain_name: str):
        w3 = get_w3(chain_name)
        latest_block = await w3.eth.block_number
        
        payments_res = await self.session.execute(
            select(Payment)
            .where(and_(Payment.status == "detected", Payment.chain == chain_name))
        )
        detected_payments = list(payments_res.scalars())
        
        confirmed_count = 0
        for payment in detected_payments:
            if payment.detected_in_block is None: continue
            confirmations = latest_block - payment.detected_in_block + 1
            if confirmations >= self.confirmations_required:
                logger.info(f"Payment {payment.id} CONFIRMED")
                payment.status = "confirmed"
                payment.confirmations = confirmations
                confirmed_count += 1
                
                # Trigger webhook if configured in env
                if settings.webhook_url:
                    payload = {
                        "payment_id": str(payment.id),
                        "status": "confirmed",
                        "address": payment.address,
                        "amount": str(payment.amount),
                        "chain": payment.chain,
                        "token_id": str(payment.token_id) if payment.token_id else None
                    }
                    send_webhook_task.send(
                        settings.webhook_url, 
                        payload, 
                        settings.webhook_secret
                    )
        
        await self.session.commit()
