from fastapi import APIRouter, Depends, status, responses
from sqlalchemy.orm import Session

from db.session import get_db
from db.models.payment import Payment
from schemas.payment import PaymentCreate, PaymentRead
from api.dependencies import get_hdwallet, get_blockchains
from utils.crypto import HDWalletManager
from datetime import datetime, timezone, timedelta

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

    try:
        # validate chain
        if payment_req.chain not in blockchains:
            raise ValueError(f"Unsupported chain: {payment_req.chain}")

        # Generate a new address using HD wallet
        address = hdwallet.get_address(index=0).get("address")

        # Real expiration logic (better to take from request if provided)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        db_payment = Payment(
            chain=payment_req.chain,
            address=address,
            amount=payment_req.amount,
            expires_at=expires_at,
        )

        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)

        return db_payment

    except Exception as e:
        return responses.JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e)},
        )