"""
Admin API endpoints for manual worker task triggering and API key management.
All endpoints require a valid X-Admin-Key header.
"""
import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import require_admin
from app.core.security import generate_api_key
from app.db.async_session import get_async_db
from app.db.models.api_key import ApiKey
from app.workers.client import get_worker_client, WorkerClient

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class SweepAddressRequest(BaseModel):
    """Request model for sweeping a specific address."""

    address: str
    chain_name: str


class ProcessPaymentRequest(BaseModel):
    """Request model for processing a specific payment."""

    payment_id: int
    chain_name: str


class CustomWebhookRequest(BaseModel):
    """Request model for sending a custom webhook."""

    url: str
    payload: Dict[str, Any]
    secret: Optional[str] = None


class JobResponse(BaseModel):
    """Response model for enqueued jobs."""

    job_id: str
    status: str
    message: str


@router.post("/scan-now", response_model=JobResponse)
async def trigger_payment_scan(client: WorkerClient = Depends(get_worker_client)):
    """
    Manually trigger an immediate payment scan across all chains.
    Useful for testing or forcing a scan outside the normal schedule.
    """
    try:
        job_id = await client.trigger_payment_scan()
        return JobResponse(
            job_id=job_id,
            status="enqueued",
            message="Payment scan triggered successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sweep-now", response_model=JobResponse)
async def trigger_fund_sweep(client: WorkerClient = Depends(get_worker_client)):
    """
    Manually trigger an immediate fund sweep across all chains.
    Sweeps confirmed payments to the main wallet.
    """
    try:
        job_id = await client.trigger_sweep()
        return JobResponse(
            job_id=job_id,
            status="enqueued",
            message="Fund sweep triggered successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sweep-address", response_model=JobResponse)
async def sweep_specific_address(
    request: SweepAddressRequest,
    client: WorkerClient = Depends(get_worker_client)
):
    """
    Sweep funds from a specific address on a specific chain.
    Useful for manual operations or recovering stuck funds.
    """
    try:
        job_id = await client.sweep_address(request.address, request.chain_name)
        return JobResponse(
            job_id=job_id,
            status="enqueued",
            message=f"Sweep triggered for {request.address} on {request.chain_name}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/process-payment", response_model=JobResponse)
async def process_payment(
    request: ProcessPaymentRequest,
    client: WorkerClient = Depends(get_worker_client)
):
    """
    Manually process a specific payment by ID.
    Useful for reprocessing failed payments or testing.
    """
    try:
        job_id = await client.process_payment(request.payment_id, request.chain_name)
        return JobResponse(
            job_id=job_id,
            status="enqueued",
            message=f"Processing payment {request.payment_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/send-webhook", response_model=JobResponse)
async def send_webhook(
    payment_id: int,
    event_type: str,
    client: WorkerClient = Depends(get_worker_client)
):
    """
    Manually send a webhook notification for a payment.
    Event types: 'payment.confirmed', 'payment.expired', 'payment.swept'
    """
    try:
        job_id = await client.send_webhook(payment_id, event_type)
        return JobResponse(
            job_id=job_id,
            status="enqueued",
            message=f"Webhook queued for payment {payment_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/custom-webhook", response_model=JobResponse)
async def send_custom_webhook(
    request: CustomWebhookRequest,
    client: WorkerClient = Depends(get_worker_client)
):
    """
    Send a custom webhook to any URL with custom payload.
    Useful for testing webhook integrations.
    """
    try:
        job_id = await client.send_custom_webhook(
            request.url,
            request.payload,
            request.secret
        )
        return JobResponse(
            job_id=job_id,
            status="enqueued",
            message=f"Custom webhook queued to {request.url}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# API Key management schemas
# ---------------------------------------------------------------------------

class ApiKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""
    name: str


class ApiKeyResponse(BaseModel):
    """Response for a created or listed API key."""
    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime.datetime
    last_used_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned once at creation — includes the raw key."""
    raw_key: str


# ---------------------------------------------------------------------------
# API Key endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Generate a new API key. The raw key is returned only once — store it securely.
    Clients must pass it as the X-Api-Key header when creating payments.
    """
    raw_key, prefix, hashed_key = generate_api_key()

    db_key = ApiKey(
        name=body.name,
        key_prefix=prefix,
        hashed_key=hashed_key,
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    return ApiKeyCreatedResponse(
        id=db_key.id,
        name=db_key.name,
        key_prefix=db_key.key_prefix,
        is_active=db_key.is_active,
        created_at=db_key.created_at,
        last_used_at=db_key.last_used_at,
        raw_key=raw_key,
    )


@router.get(
    "/api-keys",
    response_model=List[ApiKeyResponse],
    summary="List all API keys",
)
async def list_api_keys(db: AsyncSession = Depends(get_async_db)):
    """Return all API keys (active and revoked). Raw keys are never returned."""
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return result.scalars().all()


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_api_key(key_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """Deactivate an API key. The key will be rejected on subsequent requests."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    db_key = result.scalars().first()
    if not db_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    db_key.is_active = False
    await db.commit()
