from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.templates import templates
from app.db.async_session import get_async_db
from app.db.models.payment import Payment
from app.schemas.payment import PaymentRead, PaymentResponse

router = APIRouter(tags=["ui"])


@router.get("/payment/{payment_id}", response_class=HTMLResponse)
async def payment_page(
    request: Request, payment_id: str, db: AsyncSession = Depends(get_async_db)
):
    """Retrieve payment details and render the payment page."""
    # Validate payment_id format
    try:
        payment_uuid = UUID(payment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment ID format"
        )

    # get from db
    res = await db.execute(select(Payment).where(Payment.id == payment_uuid))
    db_payment = res.scalars().first()

    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    payment = PaymentResponse(
        data=PaymentRead.from_payment(db_payment)
    ).model_dump(mode="json")

    return templates.TemplateResponse(
        request=request, name="payment_page.html", context={"payment": payment["data"]}
    )
