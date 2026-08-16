"""
API endpoints for managing payments.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_wallet_manager,
    require_api_key,
)
from app.blockchain.chains import chain_by_id
from app.core.config import settings
from app.core.logger import logger
from app.db.async_session import get_async_db
from app.db.models.api_key import ApiKey
from app.db.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentRead
from app.utils.helpers import now_utc
from app.wallet import WalletKeyManager

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    payment_req: PaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    wallet_manager: WalletKeyManager = Depends(get_wallet_manager),
    api_key=Depends(require_api_key),
):
    """Create a new payment request and return the derived deposit address."""
    chain_cfg = chain_by_id(payment_req.chain_id)
    if chain_cfg is None:
        logger.warning(
            "Payment creation failed: unsupported chain_id '%s' requested by API Key ID: %s",
            payment_req.chain_id,
            api_key.id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported chain_id: {payment_req.chain_id}",
        )

    payment_id = uuid4()
    try:
        address = wallet_manager.derive_address(str(payment_id))
    except Exception as e:
        logger.error(
            "Failed to derive wallet address for payment %s: %s",
            payment_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate payment address.",
        ) from e

    token_address = (
        payment_req.token_contract_address.strip().lower()
        if payment_req.token_contract_address
        else None
    )

    db_payment = Payment(
        id=payment_id,
        user_id=api_key.user_id,
        api_key_id=api_key.id,
        chain_id=chain_cfg.chain_id,
        token_contract=token_address,
        address=address,
        amount_raw=payment_req.amount,
        expires_at=now_utc() + timedelta(minutes=settings.payment_expiry_minutes),
    )

    try:
        db.add(db_payment)
        await db.commit()
        await db.refresh(db_payment)

        logger.info(
            "Payment %s successfully created on chain '%s' "
            "with deposit address %s (API Key ID: %s)",
            payment_id,
            chain_cfg.name,
            address,
            api_key.id,
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Database error persisting payment %s: %s",
            payment_id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist payment.",
        ) from e

    # No registry update needed — the scanner reads pending payments straight
    # from the DB on its next tick (within 10s).
    return PaymentRead.from_payment(db_payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentRead,
    dependencies=[Depends(require_api_key)],
)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve a single payment by ID, including the API key name."""
    res = await db.execute(
        select(Payment, ApiKey.name)
        .outerjoin(ApiKey, Payment.api_key_id == ApiKey.id)
        .where(Payment.id == payment_id)
    )
    row = res.first()
    if not row:
        logger.warning("Payment lookup failed: ID %s not found.", payment_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    db_payment, api_key_name = row

    logger.debug("Payment metadata retrieved successfully for ID %s.", payment_id)
    return PaymentRead.from_payment(db_payment, api_key_name=api_key_name)
