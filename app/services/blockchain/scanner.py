"""
ScannerService — payment detection and lifecycle management.

Detection uses chain-sniper (WebSocket push) instead of block polling.
Call ScannerService.start_listeners() once on worker startup to begin
receiving blocks in real-time. confirm_payments() and check_expired_payments()
are still called periodically via the ARQ cron.
"""

import datetime
import asyncio
import logging
from typing import Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from chain_sniper import ChainSniper
from app.blockchain.w3 import get_w3
from app.db.async_session import AsyncSessionLocal
from app.db.models.payment import Payment, PaymentStatus
from app.db.models.token import Token
from app.services.webhook import WebhookService
from app.core.config import settings

logger = logging.getLogger(__name__)

ERC20_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)


def _get_ws_url(chain_name: str) -> str | None:
    """Return the WebSocket RPC URL for a chain from chains.yaml."""
    for chain in settings.chains:
        if chain.get("name", "").lower() == chain_name.lower():
            url = chain.get("rpc_url", "")
            if url.startswith("ws://") or url.startswith("wss://"):
                return url
    return None


class ScannerService:
    """
    Handles payment detection (via chain-sniper WebSocket listeners),
    confirmation tracking, and expiry checks.
    """

    CONFIRMATIONS_REQUIRED = 1

    def __init__(self, session: AsyncSession, confirmations_required: int = 1):
        self.session = session
        self.confirmations_required = confirmations_required

    # ------------------------------------------------------------------
    # Webhook helper
    # ------------------------------------------------------------------

    async def _dispatch_webhook(self, payment: Payment) -> None:
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
        await WebhookService.send_webhook(
            settings.webhook_url, payload, settings.webhook_secret
        )

    # ------------------------------------------------------------------
    # Confirmation & expiry (still cron-driven — no change needed here)
    # ------------------------------------------------------------------

    async def confirm_payments(self, chain_name: str) -> None:
        """Promote DETECTED payments to CONFIRMED once enough blocks have passed."""
        w3 = get_w3(chain_name)
        try:
            latest_block = await w3.eth.block_number
        except Exception as e:
            logger.error("Error getting latest block for %s: %s", chain_name, e)
            return

        result = await self.session.execute(
            select(Payment).where(
                and_(
                    Payment.status == PaymentStatus.DETECTED,
                    Payment.chain == chain_name,
                )
            )
        )
        for payment in result.scalars():
            if payment.detected_in_block is None:
                continue
            confirmations = latest_block - payment.detected_in_block + 1
            if confirmations >= self.confirmations_required:
                logger.info("Payment %s CONFIRMED", payment.id)
                payment.status = PaymentStatus.CONFIRMED
                payment.confirmations = confirmations
                await self._dispatch_webhook(payment)

        await self.session.commit()

    async def check_expired_payments(self) -> None:
        """Mark PENDING/DETECTED payments as EXPIRED past their deadline."""
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        result = await self.session.execute(
            select(Payment).where(
                and_(
                    Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.DETECTED]),
                    Payment.expires_at <= now,
                )
            )
        )
        expired = list(result.scalars())
        for payment in expired:
            logger.info("Payment %s EXPIRED", payment.id)
            payment.status = PaymentStatus.EXPIRED
            await self._dispatch_webhook(payment)

        if expired:
            await self.session.commit()

    # ------------------------------------------------------------------
    # Detection — chain-sniper WebSocket listeners
    # ------------------------------------------------------------------

    @staticmethod
    async def _on_block(block: dict, chain_name: str) -> None:
        """Handle a new full block — check native-currency transactions."""
        transactions = block.get("transactions", [])
        if not transactions:
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Payment).where(
                    and_(
                        Payment.status == PaymentStatus.PENDING,
                        Payment.chain == chain_name,
                        Payment.token_id.is_(None),
                    )
                )
            )
            pending: Dict[str, Payment] = {p.address.lower(): p for p in result.scalars()}
            if not pending:
                return

            detected = []
            for tx in transactions:
                to_addr = getattr(tx, "to", None) or tx.get("to")
                if not to_addr:
                    continue
                addr = to_addr.lower()
                if addr not in pending:
                    continue
                value = getattr(tx, "value", None) or tx.get("value", 0)
                payment = pending[addr]
                if value >= payment.amount:
                    block_number = block.get("number")
                    logger.info(
                        "[%s] Native payment detected in block %s — payment %s",
                        chain_name, block_number, payment.id,
                    )
                    payment.status = PaymentStatus.DETECTED
                    payment.detected_in_block = block_number
                    detected.append(payment)

            if detected:
                await session.commit()
                svc = ScannerService(session)
                for payment in detected:
                    await svc._dispatch_webhook(payment)

    @staticmethod
    async def _on_log(log: dict, chain_name: str) -> None:
        """Handle an ERC20 Transfer log — check recipient against pending payments."""
        topics = log.get("topics", [])
        if len(topics) < 3:
            return

        raw_to = topics[2]
        to_hex = raw_to.hex() if hasattr(raw_to, "hex") else str(raw_to)
        to_address = "0x" + to_hex[-40:].lower()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Payment).where(
                    and_(
                        Payment.status == PaymentStatus.PENDING,
                        Payment.chain == chain_name,
                        Payment.address == to_address,
                        Payment.token_id.isnot(None),
                    )
                )
            )
            payment = result.scalar_one_or_none()
            if not payment:
                return

            token_res = await session.execute(
                select(Token).where(Token.id == payment.token_id)
            )
            token = token_res.scalar_one_or_none()
            if not token:
                return

            if log.get("address", "").lower() != token.address.lower():
                return

            raw_data = log.get("data", b"")
            value = int(raw_data.hex(), 16) if raw_data else 0
            if value < payment.amount:
                return

            block_number = log.get("blockNumber")
            logger.info(
                "[%s] ERC20 payment detected in block %s — payment %s",
                chain_name, block_number, payment.id,
            )
            payment.status = PaymentStatus.DETECTED
            payment.detected_in_block = block_number
            await session.commit()
            svc = ScannerService(session)
            await svc._dispatch_webhook(payment)

    @staticmethod
    def _build_sniper(chain_name: str, ws_url: str) -> ChainSniper:
        """Configure a ChainSniper instance for one chain."""
        sniper = ChainSniper(ws_url)
        sniper.block_detail("full_block")

        async def on_block(block: dict) -> None:
            try:
                await ScannerService._on_block(block, chain_name)
            except Exception as exc:
                logger.error("[%s] Block handler error: %s", chain_name, exc, exc_info=True)

        async def on_log(log: dict) -> None:
            try:
                await ScannerService._on_log(log, chain_name)
            except Exception as exc:
                logger.error("[%s] Log handler error: %s", chain_name, exc, exc_info=True)

        async def on_error(exc: Exception) -> None:
            logger.error("[%s] ChainSniper error: %s", chain_name, exc, exc_info=True)

        sniper.on_block(on_block)
        sniper.watch(topics=[ERC20_TRANSFER_TOPIC])
        sniper.on_event(on_log)
        sniper.on_error(on_error)

        return sniper

    @staticmethod
    async def start_listeners() -> list[asyncio.Task]:
        """
        Start one ChainSniper WebSocket listener per chain in chains.yaml.
        Call this once from the ARQ worker on_startup hook.
        Returns the running asyncio Tasks (hold references to keep them alive).
        """
        tasks: list[asyncio.Task] = []

        for chain in settings.chains:
            name = chain.get("name", "").lower()
            ws_url = _get_ws_url(name)
            if not ws_url:
                logger.warning(
                    "[%s] No WebSocket URL in chains.yaml — skipping listener. "
                    "Set rpc_url to ws:// or wss://.",
                    name,
                )
                continue

            logger.info("[%s] Starting ChainSniper listener on %s", name, ws_url)
            sniper = ScannerService._build_sniper(name, ws_url)
            task = asyncio.create_task(sniper.start(), name=f"chain-sniper-{name}")
            tasks.append(task)

        return tasks
