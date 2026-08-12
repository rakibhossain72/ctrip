# API Reference

This page describes cTrip's REST endpoints, webhook mechanics, and administrative management APIs.

---

## REST Endpoints

### 1. Health Check
Checks the gateway system status.

*   **URL**: `/health`
*   **Method**: `GET`
*   **Auth Required**: No
*   **Response**:
    ```json
    {
      "status": "ok"
    }
    ```

---

### 2. Create Payment Request
Generates a unique payment deposit address and registers a pending transaction tracking session.

*   **URL**: `/api/v1/payments/`
*   **Method**: `POST`
*   **Auth Required**: Optional (Depending on API Key setup)
*   **Request Headers**:
    *   `Content-Type: application/json`
*   **Request Body**:
    ```json
    {
      "chain": "bsc",
      "amount": "25.50",
      "token_symbol": "USDT"
    }
    ```
*   **Response (Success - `201 Created`)**:
    ```json
    {
      "id": "e2a4a75e-5fb2-47ef-8d63-cf9d84bf7ff2",
      "chain": "bsc",
      "address": "0x4C0879D96c1416EDb3eC56170B7C3f645bd1D65d",
      "amount": "25.50",
      "token_symbol": "USDT",
      "status": "PENDING",
      "expires_at": "2026-08-12T19:35:00Z",
      "created_at": "2026-08-12T19:05:00Z"
    }
    ```

---

## Webhook Specifications

When a payment changes states (e.g. `DETECTED`, `CONFIRMED`, `EXPIRED`), cTrip dispatches an asynchronous `POST` request to your registered webhook target.

### Payload Structure
```json
{
  "event": "payment.confirmed",
  "timestamp": 1783933500,
  "data": {
    "payment_id": "e2a4a75e-5fb2-47ef-8d63-cf9d84bf7ff2",
    "chain": "bsc",
    "address": "0x4C0879D96c1416EDb3eC56170B7C3f645bd1D65d",
    "amount": "25.50",
    "token_symbol": "USDT",
    "tx_hash": "0x35639f72783952baefcb82910d6e190f84cb5871abf922ef6537cda38cb123aa",
    "block_number": 19483290,
    "confirmations": 3,
    "status": "CONFIRMED"
  }
}
```

### Signature Verification (HMAC-SHA256)
To secure your receiving endpoint, cTrip signs the webhook payloads. Each payload is signed using your unique `WEBHOOK_SECRET` key, and the resulting signature is sent in the `X-Webhook-Signature` request header.

Here is a Python example illustrating how to verify signatures inside your own client application:

```python
import hmac
import hashlib
from fastapi import Request, HTTPException, Header

async def verify_webhook(request: Request, x_webhook_signature: str = Header(...)):
    # Read the raw request body payload
    body = await request.body()

    # Retrieve your secure secret key
    webhook_secret = b"your-configured-webhook-secret-string"

    # Generate the expected HMAC signature
    expected_signature = hmac.new(
        key=webhook_secret,
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # Compare securely using constant-time comparison
    if not hmac.compare_digest(expected_signature, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return True
```

---

## Admin Dashboard Interface

The gateway ships with a built-in administrative management dashboard designed to speed up developer workflows and manual bookkeeping.

### Features
*   **Operational Control**: Trigger background workers manually.
*   **Payment Catalog**: View, filter, and search across payment lifecycles and historical details.
*   **Real-time Metrics**: Monitor transaction metrics, success/expiry rates, and connected blockchain RPC connectivity.
*   **Config Explorer**: View current chains loaded from `chains.yaml` along with gas price benchmarks.

To access the panel, navigate to `/admin` in your browser.
