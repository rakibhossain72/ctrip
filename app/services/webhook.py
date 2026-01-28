"""
Service for sending webhooks with optional HMAC signatures.
"""
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class WebhookService:
    """
    Service to handle dispatching webhooks to external URLs.
    """
    @staticmethod
    async def send_webhook(
        url: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None
    ) -> bool:
        """
        Send a webhook request to the given URL with the payload.
        If a secret is provided, the payload is signed using HMAC-SHA256.
        """
        try:
            data = json.dumps(payload)
            headers = {"Content-Type": "application/json"}

            if secret:
                signature = hmac.new(
                    secret.encode(),
                    data.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Webhook-Signature"] = signature

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, content=data, headers=headers)
                response.raise_for_status()
                logger.info(
                    "Webhook sent successfully to %s. Status: %s",
                    url, response.status_code
                )
                return True

        except httpx.HTTPStatusError as e:
            logger.error("Webhook failed with status %s for %s", e.response.status_code, url)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error sending webhook to %s: %s", url, e)

        return False
