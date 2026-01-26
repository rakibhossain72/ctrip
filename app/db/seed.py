from typing import Dict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import ChainState, Token
from app.blockchain.base import BlockchainBase
from app.core.config import settings


def add_chain_states(db: Session, chains: Dict[str, BlockchainBase]):
    # Add chain states
    for chain_name in chains.keys():
        existing_state = db.execute(
            select(ChainState).where(ChainState.chain == chain_name)
        ).scalar_one_or_none()
        if not existing_state:
            chain_state = ChainState(chain=chain_name, last_scanned_block=0)
            db.add(chain_state)
    
    # Add tokens from config
    for chain_cfg in settings.chains:
        chain_name = chain_cfg.get("name")
        tokens = chain_cfg.get("tokens", [])
        for token_cfg in tokens:
            symbol = token_cfg.get("symbol")
            address = token_cfg.get("address")
            decimals = token_cfg.get("decimals", 18)
            
            # Check if token already exists
            existing_token = db.execute(
                select(Token).where(
                    Token.chain == chain_name,
                    Token.symbol == symbol,
                    Token.address == address
                )
            ).scalar_one_or_none()
            
            if not existing_token:
                db.add(Token(
                    chain=chain_name,
                    symbol=symbol,
                    address=address,
                    decimals=decimals
                ))
    
    db.commit()
