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
from app.api.dependencies import get_wallet_manager, get_blockchains, require_api_key
from app.core.config import settings
from app.utils.helpers import now_utc

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
    blockchains=Depends(get_blockchains),
    api_key=Depends(require_api_key),
):
    if payment_req.chain not in blockchains:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported chain: {payment_req.chain}",
        )

    payment_id = uuid4()
    address = wallet_manager.derive_address(str(payment_id))

    db_payment = Payment(
        id=payment_id,
        chain=payment_req.chain,
        token_contract_address=payment_req.token_contract_address,
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
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist payment.",
        )

    return db_payment


@router.get(
    "/{payment_id}",
    response_model=PaymentRead,
    dependencies=[Depends(require_api_key)],  # protect this endpoint too
)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get payment details by ID.
    """
    res = await db.execute(select(Payment).where(Payment.id == payment_id))
    db_payment = res.scalars().first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    

    # get the API key name for attribution (optional)
    api_key_name = None
    if db_payment.api_key_id:
        api_key_res = await db.execute(
            select(ApiKey).where(ApiKey.id == db_payment.api_key_id)
        )
        api_key = api_key_res.scalars().first()
        if api_key:
            api_key_name = api_key.name
    payment_data = PaymentRead.from_orm(db_payment)
    payment_data.api_key_name = api_key_name
    return payment_data