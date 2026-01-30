"""
API endpoints for managing payments.
"""
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, status, responses
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.payment import Payment, HDWalletAddress
from app.db.models.token import Token
from app.schemas.payment import PaymentCreate, PaymentRead
from app.api.dependencies import get_hdwallet, get_blockchains
from app.utils.crypto import HDWalletManager

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payment_req: PaymentCreate,
    db: Session = Depends(get_db),
    hdwallet: HDWalletManager = Depends(get_hdwallet),
    blockchains=Depends(get_blockchains),
):
    """
    Create a new payment request and generate a unique receiving address.
    """
    try:
        # validate chain
        if payment_req.chain not in blockchains:
            raise ValueError(f"Unsupported chain: {payment_req.chain}")

        # validate token if provided
        if payment_req.token_id:
            token = db.query(Token).filter(
                Token.id == payment_req.token_id,
                Token.chain == payment_req.chain
            ).first()
            if not token:
                raise ValueError(
                    f"Token {payment_req.token_id} not found for chain {payment_req.chain}"
                )

        # Get the next index from HDWalletAddress
        last_addr = db.query(HDWalletAddress).order_by(HDWalletAddress.index.desc()).first()
        next_index = (last_addr.index + 1) if last_addr else 0

        # Generate a new address using HD wallet
        wallet_info = hdwallet.get_address(index=next_index)
        address = wallet_info.get("address")

        # Save the new address to track it
        db_hd_address = HDWalletAddress(
            address=address,
            index=next_index
        )
        db.add(db_hd_address)

        # Real expiration logic (better to take from request if provided)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        db_payment = Payment(
            chain=payment_req.chain,
            token_id=payment_req.token_id,
            address=address,
            amount=payment_req.amount,
            expires_at=expires_at,
        )

        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)

        return db_payment

    except Exception as e:  # pylint: disable=broad-exception-caught
        # rollback in case of error
        db.rollback()
        return responses.JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
        )
@router.get(
    "/{payment_id}",
    response_model=PaymentRead,
)
def get_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get payment details by ID.
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return db_payment
