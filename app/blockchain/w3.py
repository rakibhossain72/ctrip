from web3 import AsyncWeb3
from blockchain.manager import get_blockchains

_blockchains = get_blockchains()
_w3_cache = {}

def get_w3(chain_name: str) -> AsyncWeb3:
    if chain_name not in _w3_cache:
        blockchain = _blockchains[chain_name]
        _w3_cache[chain_name] = AsyncWeb3(
            blockchain.get_async_provider()
        )
    return _w3_cache[chain_name]