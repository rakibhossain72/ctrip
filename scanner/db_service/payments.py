from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models import Payment, PaymentWallet, PaymentStatus
from datetime import datetime, timezone


# read / queries
async def get_payment_by_address(db: AsyncSession, address: str) -> Payment | None:
    """Fetch a Payment by its address."""
    result = await db.execute(select(Payment).where(Payment.address == address))
    return result.scalar_one_or_none()


async def get_payments_by_addresses(
    db: AsyncSession, addresses: list[str]
) -> dict[str, Payment]:
    result = await db.execute(
        select(Payment)
        .where(Payment.address.in_(addresses))
        .where(Payment.status == PaymentStatus.PENDING)
    )
    return {p.address: p for p in result.scalars().all()}


async def get_payment_wallet_by_address(
    db: AsyncSession, address: str
) -> PaymentWallet | None:
    """Fetch a PaymentWallet by its address."""
    result = await db.execute(
        select(PaymentWallet).where(PaymentWallet.address == address)
    )
    return result.scalar_one_or_none()


# write / updates
async def update_payment_status(
    db: AsyncSession, payment_id: int, new_status: PaymentStatus
) -> bool:
    """Update the status of a Payment in a single round-trip.

    Returns True if a row was updated, False if no matching payment existed.
    """
    result = await db.execute(
        update(Payment).where(Payment.id == payment_id).values(status=new_status)
    )
    await db.commit()
    return result.rowcount > 0


async def update_payment_confirmations(
    db: AsyncSession, payment_id: int, new_confirmations: int
) -> bool:
    """Update the confirmations count of a Payment in a single round-trip.

    Returns True if a row was updated, False if no matching payment existed.
    """
    result = await db.execute(
        update(Payment)
        .where(Payment.id == payment_id)
        .values(confirmations=new_confirmations, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount > 0


async def update_payment_detected_block(
    db: AsyncSession, payment_id: int, detected_in_block: int
) -> bool:
    """Update the detected_in_block of a Payment in a single round-trip.

    Returns True if a row was updated, False if no matching payment existed.
    """
    result = await db.execute(
        update(Payment)
        .where(Payment.id == payment_id)
        .values(
            detected_in_block=detected_in_block, updated_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()
    return result.rowcount > 0


async def update_payment(db: AsyncSession, payment_id: int, **updates) -> bool:
    """Update a Payment with the given fields in a single round-trip.

    Returns True if a row was updated, False if no matching payment existed.
    """
    result = await db.execute(
        update(Payment)
        .where(Payment.id == payment_id)
        .values(**updates, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount > 0
