"""
API endpoints for managing payments.
"""
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.db.async_session import get_async_db
from app.db.models.payment import Payment
from app.db.models.wallets import HDWalletAddress
from app.db.models.api_key import ApiKey
from app.db.models.token import Token
from app.schemas.payment import PaymentCreate, PaymentRead
from app.api.dependencies import get_hdwallet, get_blockchains, require_api_key
from app.utils.crypto import HDWalletManager
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
    hdwallet: HDWalletManager = Depends(get_hdwallet),
    blockchains=Depends(get_blockchains),
    api_key=Depends(require_api_key),  # single injection point
):
    """
    Create a new payment request and generate a unique receiving address.
    """
    # Attach the API key ID to the payment for attribution
    payment_req.api_key_id = api_key.id

    # Validate chain
    if payment_req.chain not in blockchains:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported chain: {payment_req.chain}",
        )

    # Validate token if provided
    if payment_req.token_id:
        token_res = await db.execute(
            select(Token).where(
                Token.id == payment_req.token_id,
                Token.chain == payment_req.chain,
            )
        )
        if not token_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Token {payment_req.token_id} not found for chain {payment_req.chain}",
            )

    try:
        index_res = await db.execute(select(func.coalesce(func.max(HDWalletAddress.index), -1)))
        next_index = index_res.scalar() + 1

        wallet_info = hdwallet.get_address(index=next_index)
        address = wallet_info["address"]

        db.add(HDWalletAddress(address=address, index=next_index))
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Address index conflict, please retry.",
        )

    expires_at = now_utc() + timedelta(minutes=30)

    db_payment = Payment(
        chain=payment_req.chain,
        token_id=payment_req.token_id,
        address=address,
        amount=payment_req.amount,
        expires_at=expires_at,
        api_key_id=api_key.id,
    )
    db.add(db_payment)

    await db.commit()
    await db.refresh(db_payment)

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