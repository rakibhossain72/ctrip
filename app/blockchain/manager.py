from core.config import settings
from blockchain.anvil import AnvilBlockchain
from blockchain.base import BlockchainBase
from typing import Dict

def get_anvil_blockchain() -> AnvilBlockchain:
    """
    Create and return an AnvilBlockchain instance.
    """
    # Use the RPC URL from settings, defaulting to what was used in main.py if not present
    return AnvilBlockchain(provider_url=settings.rpc_url)

def get_blockchains() -> Dict[str, BlockchainBase]:
    """
    Return a dictionary of configured blockchains.
    Useful for populating app.state.blockchains or for use in workers.
    """
    blockchains = {}
    for chain_cfg in settings.chains:
        name = chain_cfg.get("name")
        rpc_url = chain_cfg.get("rpc_url")
        if name and rpc_url:
            # For now, we use BlockchainBase as the base implementation
            # In a real app, you might have different classes for different chains
            blockchains[name] = BlockchainBase(provider_url=rpc_url)
    
    # Fallback if config is empty
    if not blockchains:
        blockchains["anvil"] = AnvilBlockchain(provider_url=settings.rpc_url)
        
    return blockchains
