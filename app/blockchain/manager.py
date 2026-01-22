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
    return {
        "anvil": get_anvil_blockchain()
    }
