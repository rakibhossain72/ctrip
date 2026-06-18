from typing import List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import require_admin
from app.core.security import generate_api_key
from app.db.async_session import get_async_db
from app.db.models.api_key import ApiKey
from app.workers.client import get_worker_client, WorkerClient
from app.schemas.admin import (
    SweepAddressRequest,
    ProcessPaymentRequest,
    CustomWebhookRequest,
    JobResponse,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/scan-now", response_model=JobResponse)
async def trigger_payment_scan(client: WorkerClient = Depends(get_worker_client)):
    """Manually trigger an immediate payment scan across all chains."""
    try:
        job_id = await client.trigger_payment_scan()
        return JobResponse(job_id=job_id, status="enqueued", message="Payment scan triggered successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sweep-now", response_model=JobResponse)
async def trigger_fund_sweep(client: WorkerClient = Depends(get_worker_client)):
    """Manually trigger an immediate fund sweep across all chains."""
    try:
        job_id = await client.trigger_sweep()
        return JobResponse(job_id=job_id, status="enqueued", message="Fund sweep triggered successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sweep-address", response_model=JobResponse)
async def sweep_specific_address(
    request: SweepAddressRequest,
    client: WorkerClient = Depends(get_worker_client),
):
    """Sweep funds from a specific address on a specific chain."""
    try:
        job_id = await client.sweep_address(request.address, request.chain_name)
        return JobResponse(job_id=job_id, status="enqueued", message=f"Sweep triggered for {request.address} on {request.chain_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/process-payment", response_model=JobResponse)
async def process_payment(
    request: ProcessPaymentRequest,
    client: WorkerClient = Depends(get_worker_client),
):
    """Manually process a specific payment by ID."""
    try:
        job_id = await client.process_payment(request.payment_id, request.chain_name)
        return JobResponse(job_id=job_id, status="enqueued", message=f"Processing payment {request.payment_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/send-webhook", response_model=JobResponse)
async def send_webhook(
    payment_id: int,
    event_type: str,
    client: WorkerClient = Depends(get_worker_client),
):
    """Manually send a webhook notification for a payment."""
    try:
        job_id = await client.send_webhook(payment_id, event_type)
        return JobResponse(job_id=job_id, status="enqueued", message=f"Webhook queued for payment {payment_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/custom-webhook", response_model=JobResponse)
async def send_custom_webhook(
    request: CustomWebhookRequest,
    client: WorkerClient = Depends(get_worker_client),
):
    """Send a custom webhook to any URL with a custom payload."""
    try:
        job_id = await client.send_custom_webhook(request.url, request.payload, request.secret)
        return JobResponse(job_id=job_id, status="enqueued", message=f"Custom webhook queued to {request.url}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(body: ApiKeyCreateRequest, db: AsyncSession = Depends(get_async_db)):
    """Generate a new API key. The raw key is returned only once."""
    raw_key, prefix, hashed_key = generate_api_key()

    db_key = ApiKey(name=body.name, key_prefix=prefix, hashed_key=hashed_key, created_at=datetime.now(timezone.utc).replace(tzinfo=None))
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


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(db: AsyncSession = Depends(get_async_db)):
    """Return all API keys (active and revoked). Raw keys are never returned."""
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return result.scalars().all()


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """Deactivate an API key."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    db_key = result.scalars().first()
    if not db_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    db_key.is_active = False
    await db.commit()
