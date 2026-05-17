"""
Worker for sending webhook notifications.
"""
import dataclasses
import datetime
import json
from typing import Dict, Any, Optional

from sqlalchemy import select, and_

from app.db.async_session import AsyncSessionLocal as async_session
from app.db.models.payment import Payment
from app.db.models.webhook_attempt import WebhookAttempt, WebhookAttemptStatus
from app.services.webhook import WebhookService
from app.core.logger import logger
from app.core.config import settings


@dataclasses.dataclass
class _AttemptParams:
    """Groups webhook attempt creation parameters to stay within argument limits."""

    payment_id: str
    event_type: str
    webhook_url: str
    payload: Dict[str, Any]
    webhook_secret: Optional[str]


async def _record_attempt(session, params: _AttemptParams) -> WebhookAttempt:
    """Create and persist a new WebhookAttempt record."""
    attempt = WebhookAttempt(
        payment_id=str(params.payment_id),
        event_type=params.event_type,
        webhook_url=params.webhook_url,
        payload=json.dumps(params.payload),
        webhook_secret=params.webhook_secret,
        status=WebhookAttemptStatus.PENDING,
    )
    session.add(attempt)
    await session.flush()
    return attempt


async def _deliver(attempt: WebhookAttempt) -> bool:
    """
    Try to deliver a webhook attempt.
    Updates the attempt record in-place; caller must commit.
    """
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    payload = json.loads(attempt.payload)

    success = await WebhookService.send_webhook(
        attempt.webhook_url, payload, attempt.webhook_secret
    )

    attempt.retry_count += 1
    attempt.updated_at = now

    if success:
        attempt.status = WebhookAttemptStatus.SUCCESS
        attempt.next_retry_at = None
        attempt.last_error = None
    else:
        if attempt.retry_count >= WebhookAttempt.MAX_RETRIES:
            attempt.status = WebhookAttemptStatus.FAILED
            attempt.next_retry_at = None
            logger.warning(
                "Webhook permanently failed after %d retries (attempt %s)",
                WebhookAttempt.MAX_RETRIES, attempt.id,
            )
        else:
            attempt.status = WebhookAttemptStatus.PENDING
            delay = WebhookAttempt.BACKOFF_SECONDS[attempt.retry_count - 1]
            attempt.next_retry_at = now + datetime.timedelta(seconds=delay)
            logger.info(
                "Webhook attempt %s failed, retry %d/%d in %ds",
                attempt.id, attempt.retry_count, WebhookAttempt.MAX_RETRIES, delay,
            )

    return success


async def send_webhook_notification(ctx, payment_id: int, event_type: str):  # pylint: disable=unused-argument
    """
    Send webhook notification for a payment event.
    Records the attempt and retries automatically on failure.

    Args:
        payment_id: The payment ID
        event_type: Type of event (e.g., 'payment.confirmed', 'payment.expired')
    """
    try:
        logger.info("Sending webhook for payment %s, event: %s", payment_id, event_type)

        async with async_session() as session:
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                logger.warning("Payment %s not found", payment_id)
                return False

            webhook_url = getattr(payment, 'webhook_url', None) or settings.webhook_url
            if not webhook_url:
                logger.info("No webhook URL configured for payment %s", payment_id)
                return True

            payload = {
                "event": event_type,
                "payment_id": str(payment.id),
                "address": payment.address,
                "amount": str(payment.amount),
                "chain": payment.chain,
                "status": payment.status.value,
            }

            webhook_secret = settings.webhook_secret
            attempt = await _record_attempt(
                session,
                _AttemptParams(payment.id, event_type, webhook_url, payload, webhook_secret),
            )

            success = await _deliver(attempt)
            await session.commit()

            return success

    except Exception as e:
        logger.error("Error sending webhook for payment %s: %s", payment_id, e, exc_info=True)
        raise


async def retry_failed_webhooks(ctx):  # pylint: disable=unused-argument
    """
    Retry pending webhook attempts whose next_retry_at is due.
    Runs every 5 minutes via cron.
    Uses exponential backoff — see WebhookAttempt.BACKOFF_SECONDS.
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        logger.info("retry_failed_webhooks: checking for due retries at %s", now)

        async with async_session() as session:
            result = await session.execute(
                select(WebhookAttempt).where(
                    and_(
                        WebhookAttempt.status == WebhookAttemptStatus.PENDING,
                        WebhookAttempt.next_retry_at <= now,
                        WebhookAttempt.retry_count < WebhookAttempt.MAX_RETRIES,
                    )
                )
            )
            due = list(result.scalars())

            if not due:
                logger.info("retry_failed_webhooks: no retries due")
                return

            logger.info("retry_failed_webhooks: retrying %d attempt(s)", len(due))
            succeeded = 0
            for attempt in due:
                success = await _deliver(attempt)
                if success:
                    succeeded += 1

            await session.commit()
            logger.info(
                "retry_failed_webhooks: %d/%d succeeded", succeeded, len(due)
            )

    except Exception as e:
        logger.error("Error in retry_failed_webhooks: %s", e, exc_info=True)
        raise


async def send_custom_webhook(ctx, url: str, payload: Dict[str, Any], secret: Optional[str] = None):  # pylint: disable=unused-argument
    """
    Send a custom webhook to any URL.
    Useful for testing or manual notifications.
    """
    try:
        logger.info("Sending custom webhook to %s", url)

        success = await WebhookService.send_webhook(url, payload, secret)

        if success:
            logger.info("Custom webhook sent successfully to %s", url)
        else:
            logger.warning("Custom webhook failed for %s", url)

        return success

    except Exception as e:
        logger.error("Error sending custom webhook: %s", e, exc_info=True)
        raise
