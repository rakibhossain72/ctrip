import hmac
import hashlib
import json
import logging
import httpx
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class WebhookService:
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
                logger.info(f"Webhook sent successfully to {url}. Status: {response.status_code}")
                return True
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Webhook failed with status {e.response.status_code} for {url}")
        except Exception as e:
            logger.error(f"Error sending webhook to {url}: {e}")
            
        return False
