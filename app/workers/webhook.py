"""
Worker for sending webhook notifications.
"""
from typing import Dict, Any
from app.db.async_session import AsyncSessionLocal as async_session
from app.services.webhook_service import WebhookService
from app.core.logger import logger


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
            webhook_service = WebhookService(session)
            success = await webhook_service.send_payment_webhook(payment_id, event_type)
            
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
    """
    try:
        logger.info("ARQ task: retry_failed_webhooks triggered")
        
        async with async_session() as session:
            webhook_service = WebhookService(session)
            retried_count = await webhook_service.retry_failed_webhooks()
            
            if retried_count > 0:
                logger.info(f"Retried {retried_count} failed webhooks")

        logger.info("Webhook retry cycle complete")
        
    except Exception as e:
        logger.error("Error in webhook retry: %s", e, exc_info=True)
        raise


async def send_custom_webhook(ctx, url: str, payload: Dict[str, Any], secret: str = None):
    """
    Send a custom webhook to any URL.
    Useful for testing or manual notifications.
    """
    try:
        logger.info(f"Sending custom webhook to {url}")
        
        async with async_session() as session:
            webhook_service = WebhookService(session)
            success = await webhook_service.send_custom_webhook(url, payload, secret)
            
        return success
        
    except Exception as e:
        logger.error(f"Error sending custom webhook: {e}", exc_info=True)
        raise
