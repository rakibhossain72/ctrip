from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from db.session import get_db
from db.models.payment import Payment, PaymentStatus
from db.models.merchant import Merchant
from schemas.payment import PaymentCreate, PaymentRead
from api.dependencies import get_anvil, get_hdwallet
from blockchain.anvil import AnvilBlockchain
from datetime import datetime, timezone, timedelta
from decimal import Decimal

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payment_req: PaymentCreate,
    db: Session = Depends(get_db),
    anvil: AnvilBlockchain = Depends(get_anvil),
    hdwallet = Depends(get_hdwallet)
):
    # ── Security step you are missing ───────────────────────────────
    # Current_merchant = Depends(get_current_merchant)  # you need this
    # if payment_req.merchant_id != current_merchant.id:
    #     raise HTTPException(403, "Not your merchant")

    try:
        merchant = db.query(Merchant).filter(Merchant.id == payment_req.merchant_id).one()
    except NoResultFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Merchant not found")

    
    address = hdwallet.get_address(index=0)
    

    # Real expiration logic (better to take from request if provided)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    db_payment = Payment(
        merchant_id=payment_req.merchant_id,
        chain=payment_req.chain,
        address=address,
        amount=payment_req.amount,
        expires_at=expires_at,
        status=PaymentStatus.pending,
        confirmations=0,
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)

    return db_payment