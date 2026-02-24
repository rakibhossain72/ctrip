"""
Admin API endpoints for manual worker task triggering.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.workers.client import get_worker_client, WorkerClient

router = APIRouter(prefix="/admin", tags=["admin"])


class SweepAddressRequest(BaseModel):
    address: str
    chain_name: str


class ProcessPaymentRequest(BaseModel):
    payment_id: int
    chain_name: str


class CustomWebhookRequest(BaseModel):
    url: str
    payload: Dict[str, Any]
    secret: Optional[str] = None


class JobResponse(BaseModel):
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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    client: WorkerClient = Depends(get_worker_client)
):
    """
    Get the status and result of a background job.
    Returns job status, result, and any error information.
    """
    try:
        status = await client.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
