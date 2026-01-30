"""
Service for scaning blocks from blockchain to check payments
"""

import datetime
import logging
from dataclasses import dataclass
from typing import Dict
from sqlalchemy import select, and_
from app.blockchain.w3 import get_w3
from app.db.models.payment import Payment, PaymentStatus
from app.db.models.chain import ChainState
from app.db.models.token import Token
from app.services.webhook import WebhookService
from app.core.config import settings

logger = logging.getLogger(__name__)

ERC20_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)


@dataclass
class PaymentScanContext:
    """Context object for payment scanning to reduce method arguments."""

    native_payments: Dict[str, Payment]
    erc20_payments: Dict[str, Payment]
    tokens: Dict[int, Token]


class ScannerService:
    """
    ScannerService finds payments on various blockchains and handles expiration.
    """

    def __init__(self, session, confirmations_required=1, block_batch_size=20):
        self.session = session
        self.confirmations_required = confirmations_required
        self.block_batch_size = block_batch_size

    async def _dispatch_webhook(self, payment: Payment):
        """Helper to send webhook notifications directly."""
        if not settings.webhook_url:
            return

        payload = {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "address": payment.address,
            "amount": str(payment.amount),
            "chain": payment.chain,
            "token_id": str(payment.token_id) if payment.token_id else None,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        # Direct call to the service as requested
        await WebhookService.send_webhook(
            settings.webhook_url, payload, settings.webhook_secret
        )

    # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
    async def scan_chain(self, chain_name: str):
        """Scan a specific chain for pending payments."""
        logger.info("Scanning chain: %s", chain_name)

        w3 = get_w3(chain_name)
        state = await self._load_chain_state(chain_name)

        if not state:
            logger.warning("No chain state found for %s, skipping", chain_name)
            return

        from_block, to_block = await self._calculate_scan_range(w3, state)
        if from_block > to_block:
            return

        payments_res = await self.session.execute(
            select(Payment).where(
                and_(
                    Payment.status == PaymentStatus.PENDING, Payment.chain == chain_name
                )
            )
        )
        payment_list = list(payments_res.scalars())

        if not payment_list:
            state.last_scanned_block = to_block
            await self.session.commit()
            return

        native_payments = {
            p.address.lower(): p for p in payment_list if p.token_id is None
        }
        erc20_payments = {
            p.address.lower(): p for p in payment_list if p.token_id is not None
        }

        # Pre-load tokens for ERC20 payments to avoid DB calls in the loop
        tokens = {}
        if erc20_payments:
            token_ids = {p.token_id for p in erc20_payments.values()}
            tokens_res = await self.session.execute(
                select(Token).where(Token.id.in_(token_ids))
            )
            tokens = {t.id: t for t in tokens_res.scalars()}

        # Create context object to reduce method arguments
        scan_context = PaymentScanContext(
            native_payments=native_payments,
            erc20_payments=erc20_payments,
            tokens=tokens,
        )

        detected_count = await self._scan_blocks_for_payments(
            w3=w3,
            from_block=from_block,
            to_block=to_block,
            context=scan_context,
        )

        state.last_scanned_block = to_block
        await self.session.commit()
        logger.info("Scan complete for %s. Detected: %s", chain_name, detected_count)

    async def confirm_payments(self, chain_name: str):
        """Check for confirmations of detected payments."""
        w3 = get_w3(chain_name)
        latest_block = await w3.eth.block_number

        payments_res = await self.session.execute(
            select(Payment).where(
                and_(
                    Payment.status == PaymentStatus.DETECTED,
                    Payment.chain == chain_name,
                )
            )
        )
        detected_payments = list(payments_res.scalars())

        confirmed_count = 0
        for payment in detected_payments:
            if payment.detected_in_block is None:
                continue
            confirmations = latest_block - payment.detected_in_block + 1
            if confirmations >= self.confirmations_required:
                logger.info("Payment %s CONFIRMED", payment.id)
                payment.status = PaymentStatus.CONFIRMED
                payment.confirmations = confirmations
                confirmed_count += 1
                await self._dispatch_webhook(payment)

        await self.session.commit()

    async def check_expired_payments(self):
        """Check and mark payments as expired if they reached their deadline."""
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        payments_res = await self.session.execute(
            select(Payment).where(
                and_(
                    Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.DETECTED]),
                    Payment.expires_at <= now,
                )
            )
        )
        expired_payments = list(payments_res.scalars())

        for payment in expired_payments:
            logger.info("Payment %s EXPIRED", payment.id)
            payment.status = PaymentStatus.EXPIRED
            await self._dispatch_webhook(payment)

        if expired_payments:
            await self.session.commit()

    async def _calculate_scan_range(self, w3, state):
        latest_block = await w3.eth.block_number
        from_block = state.last_scanned_block + 1
        to_block = min(from_block + self.block_batch_size, latest_block)
        return from_block, to_block

    async def _load_chain_state(self, chain_name):
        state_res = await self.session.execute(
            select(ChainState).where(ChainState.chain == chain_name).with_for_update()
        )
        return state_res.scalar_one_or_none()

    async def _scan_blocks_for_payments(
        self, w3, from_block: int, to_block: int, context: PaymentScanContext
    ):
        """Scan blocks for native and ERC20 payments."""
        detected_count = 0

        for block_number in range(from_block, to_block + 1):
            block = await w3.eth.get_block(block_number, full_transactions=True)

            # Native transfers
            for tx in block.transactions:
                if not tx.to:
                    continue
                addr = tx.to.lower()
                if addr in context.native_payments:
                    payment = context.native_payments[addr]
                    if tx.value >= payment.amount:
                        logger.info("Native Payment detected! ID: %s", payment.id)
                        payment.status = PaymentStatus.DETECTED
                        payment.detected_in_block = block_number
                        detected_count += 1
                        await self._dispatch_webhook(payment)

            # ERC20 transfers
            if context.erc20_payments:
                logs = await w3.eth.get_logs(
                    {
                        "from_block": block_number,
                        "to_block": block_number,
                        "topics": [ERC20_TRANSFER_TOPIC],
                    }
                )
                for log in logs:
                    if len(log.topics) < 3:
                        continue
                    to_address = "0x" + log.topics[2].hex()[-40:].lower()
                    if to_address in context.erc20_payments:
                        payment = context.erc20_payments[to_address]
                        token = context.tokens.get(payment.token_id)
                        if token and log.address.lower() == token.address.lower():
                            value = int(log.data.hex(), 16) if log.data else 0
                            if value >= payment.amount:
                                logger.info(
                                    "ERC20 Payment detected! ID: %s", payment.id
                                )
                                payment.status = PaymentStatus.DETECTED
                                payment.detected_in_block = block_number
                                detected_count += 1
                                await self._dispatch_webhook(payment)
        return detected_count
