from app.core.config import settings
from app.blockchain.anvil import AnvilBlockchain
from app.blockchain.ethereum import EthereumBlockchain
from app.blockchain.bsc import BSCBlockchain
from app.blockchain.base import BlockchainBase
from typing import Dict

def get_blockchains() -> Dict[str, BlockchainBase]:
    """
    Return a dictionary of configured blockchains.
    """
    blockchains = {}
    for chain_cfg in settings.chains:
        name = (chain_cfg.get("name") or "").lower()
        rpc_url = chain_cfg.get("rpc_url")
        if not rpc_url:
            continue
            
        if name == "ethereum":
            blockchains[name] = EthereumBlockchain(provider_url=rpc_url)
        elif name == "bsc":
            blockchains[name] = BSCBlockchain(provider_url=rpc_url)
        elif name == "anvil":
            blockchains[name] = AnvilBlockchain(provider_url=rpc_url)
        else:
            blockchains[name] = BlockchainBase(provider_url=rpc_url)
    
    # Fallback if config is empty
    if not blockchains:
        blockchains["anvil"] = AnvilBlockchain(provider_url=settings.rpc_url)
        
    return blockchains
