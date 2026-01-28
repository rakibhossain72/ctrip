"""
Worker for processing webhook tasks using Dramatiq.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

import dramatiq
from app.services.webhook import WebhookService

logger = logging.getLogger(__name__)

# Use the same loop for async operations in the actor
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)


@dramatiq.actor(max_retries=3)
def send_webhook_task(
    url: str,
    payload: Dict[str, Any],
    secret: Optional[str] = None
):
    """
    Dramatiq actor to send webhooks asynchronously.
    """
    logger.info("Processing webhook task for %s", url)

    async def run():
        success = await WebhookService.send_webhook(url, payload, secret)
        if not success:
            # We raise an exception here to trigger dramatiq retries
            raise RuntimeError(f"Failed to send webhook to {url}")

    try:
        _loop.run_until_complete(run())
    except Exception as e:
        logger.error("Webhook actor error: %s", e)
        raise  # Let dramatiq handle retries
