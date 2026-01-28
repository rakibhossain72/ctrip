"""
Database model for tracking the state of each scanned blockchain.
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.schema import UniqueConstraint
from app.db.base import Base


# pylint: disable=too-few-public-methods
class ChainState(Base):
    """
    Tracks the last scanned block for each configured blockchain.
    """
    __tablename__ = "chain_states"
    id = Column(Integer, primary_key=True, index=True)
    chain = Column(String, nullable=False)
    last_scanned_block = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('chain', name='uq_chain_states_chain'),
    )
