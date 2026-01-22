from typing import Dict
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.models import ChainState
from blockchain.base import BlockchainBase

def add_chain_states(db: Session, chains: Dict[str, BlockchainBase]):
    for chain_name in chains.keys():
        existing_state = db.execute(
            select(ChainState).where(ChainState.chain == chain_name)
        ).scalar_one_or_none()
        if not existing_state:
            chain_state = ChainState(chain=chain_name, last_scanned_block=0)
            db.add(chain_state)
    db.commit()
