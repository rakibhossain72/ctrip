"""
Worker for sending webhook notifications.
"""
from typing import Dict, Any, Optional
from sqlalchemy import select
from app.db.async_session import AsyncSessionLocal as async_session
from app.db.models.payment import Payment
from app.services.webhook import WebhookService
from app.core.logger import logger
from app.core.config import settings


async def send_webhook_notification(ctx, payment_id: int, event_type: str):
    """
    Send webhook notification for a payment event.
    
    Args:
        payment_id: The payment ID
        event_type: Type of event (e.g., 'payment.confirmed', 'payment.expired')
    """
    try:
        logger.info(f"Sending webhook for payment {payment_id}, event: {event_type}")
        
        async with async_session() as session:
            # Get payment details
            result = await session.execute(
                select(Payment).where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.warning(f"Payment {payment_id} not found")
                return False
            
            # Check if webhook URL is configured
            webhook_url = payment.webhook_url or settings.webhook_url
            if not webhook_url:
                logger.info(f"No webhook URL configured for payment {payment_id}")
                return True  # Not an error, just no webhook configured
            
            # Prepare payload
            payload = {
                "event": event_type,
                "payment_id": payment.id,
                "address": payment.address,
                "amount": str(payment.amount),
                "token": payment.token,
                "chain": payment.chain,
                "status": payment.status,
                "tx_hash": payment.tx_hash,
            }
            
            # Send webhook
            webhook_secret = settings.webhook_secret
            success = await WebhookService.send_webhook(webhook_url, payload, webhook_secret)
            
            if success:
                logger.info(f"Webhook sent successfully for payment {payment_id}")
            else:
                logger.warning(f"Webhook failed for payment {payment_id}")
                
            return success
        
    except Exception as e:
        logger.error(f"Error sending webhook for payment {payment_id}: {e}", exc_info=True)
        raise


async def retry_failed_webhooks(ctx):
    """
    Retry webhooks that previously failed.
    Runs every 5 minutes via cron.
    
    Note: This is a placeholder. Implement webhook retry logic with a
    separate webhook_attempts table to track failures and retries.
    """
    try:
        logger.info("="*60)
        logger.info("🔄 ARQ task: retry_failed_webhooks triggered")
        logger.info("="*60)
        
        # TODO: Implement webhook retry logic
        # 1. Query webhook_attempts table for failed webhooks
        # 2. Filter by retry count < max_retries
        # 3. Retry each webhook
        # 4. Update retry count and status
        
        logger.info("🔄 Webhook retry cycle complete (placeholder)")
        logger.info("="*60)
        
    except Exception as e:
        logger.error("❌ Error in webhook retry: %s", e, exc_info=True)
        raise


async def send_custom_webhook(ctx, url: str, payload: Dict[str, Any], secret: Optional[str] = None):
    """
    Send a custom webhook to any URL.
    Useful for testing or manual notifications.
    """
    try:
        logger.info(f"Sending custom webhook to {url}")
        
        success = await WebhookService.send_webhook(url, payload, secret)
        
        if success:
            logger.info(f"Custom webhook sent successfully to {url}")
        else:
            logger.warning(f"Custom webhook failed for {url}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error sending custom webhook: {e}", exc_info=True)
        raise
