"""
API endpoints for managing payments.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, status
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.async_session import get_async_db
from app.db.models.payment import Payment
from app.db.models.api_key import ApiKey

from app.db.models.wallets import PaymentWallet
from app.wallet import WalletKeyManager

from app.schemas.payment import PaymentCreate, PaymentRead
from app.api.dependencies import (
    get_wallet_manager,
    require_api_key,
)
from app.blockchain.chains import chain_by_id
from app.core.config import settings
from app.utils.helpers import now_utc
from app.core.logger import logger


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
    chain_cfg = chain_by_id(payment_req.chain_id)
    if chain_cfg is None:
        logger.warning(
            f"Payment creation failed: unsupported chain_id '{payment_req.chain_id}' "
            f"requested by API Key ID: {api_key.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported chain_id: {payment_req.chain_id}",
        )

    payment_id = uuid4()
    try:
        address = wallet_manager.derive_address(str(payment_id))
    except Exception as e:
        logger.error(f"Failed to derive wallet address for payment {payment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate payment address.",
        )

    token_address = (
        payment_req.token_contract_address.strip().lower()
        if payment_req.token_contract_address
        else None
    )

    db_payment = Payment(
        id=payment_id,
        chain=chain_cfg.name,
        chain_id=chain_cfg.chain_id,
        token_contract_address=token_address,
        address=address,
        amount=payment_req.amount,
        expires_at=now_utc() + timedelta(minutes=settings.payment_expiry_minutes),
        api_key_id=api_key.id,
    )
    db_wallet = PaymentWallet(
        payment_id=payment_id,
        address=address,
    )

    try:
        db.add(db_payment)
        db.add(db_wallet)
        await db.commit()
        await db.refresh(db_payment)

        logger.info(
            f"Payment {payment_id} successfully created on chain '{chain_cfg.name}' "
            f"with deposit address {address} (API Key ID: {api_key.id})"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Database error persisting payment {payment_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist payment.",
        )

    # No registry update needed — the scanner reads pending payments straight
    # from the DB on its next tick (within 10s).
    return db_payment


@router.get(
    "/{payment_id}",
    response_model=PaymentRead,
    dependencies=[Depends(require_api_key)],
)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    res = await db.execute(select(Payment).where(Payment.id == payment_id))
    db_payment = res.scalars().first()

    if not db_payment:
        logger.warning(f"Payment lookup failed: ID {payment_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    api_key_name = None
    if db_payment.api_key_id:
        api_key_res = await db.execute(
            select(ApiKey).where(ApiKey.id == db_payment.api_key_id)
        )
        api_key = api_key_res.scalars().first()
        if api_key:
            api_key_name = api_key.name
        else:
            logger.warning(
                f"API Key ID {db_payment.api_key_id} associated with payment {payment_id} "
                "could not be found in the database."
            )

    logger.debug(f"Payment metadata retrieved successfully for ID {payment_id}.")

    payment_data = PaymentRead.from_orm(db_payment)
    payment_data.api_key_name = api_key_name
    return payment_data
