"""
chain
last_scanned_block
"""
from sqlalchemy import Column, Integer, String
from db.base import Base
from sqlalchemy.schema import UniqueConstraint

class ChainState(Base):
    __tablename__ = "chain_states"
    id = Column(Integer, primary_key=True, index=True)
    chain = Column(String, nullable=False)
    last_scanned_block = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('chain', name='uq_chain_states_chain'),
    )