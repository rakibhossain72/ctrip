import datetime

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# pylint: disable=too-few-public-methods
class HDWalletAddress(Base):
    __tablename__ = "hdwallet_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_swapped: Mapped[bool] = mapped_column(default=False, nullable=False)
    index: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False
    )  # no sequence
    address: Mapped[str] = mapped_column(unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), nullable=False
    )
