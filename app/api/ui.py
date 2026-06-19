from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.async_session import get_async_db
from app.db.models.payment import Payment
from app.schemas.payment import PaymentResponse, PaymentRead


router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")


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

    payment = PaymentResponse(
        data=PaymentRead.model_validate(db_payment)
    ).model_dump(mode="json")


    if not db_payment or not payment["data"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    

    return templates.TemplateResponse(
        request=request, name="payment_page.html", context={"payment": payment["data"]}
    )
