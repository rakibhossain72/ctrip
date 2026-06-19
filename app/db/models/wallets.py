import datetime

from sqlalchemy import Integer, DateTime, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class PaymentWallet(Base):
    __tablename__ = "payment_wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    address: Mapped[str] = mapped_column(unique=True, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_swapped: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(
            tzinfo=None
        ),
        nullable=False,
    )