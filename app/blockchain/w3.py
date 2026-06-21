"""
Utility for accessing the AsyncWeb3 instance for a given chain name.
"""

from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers import AsyncHTTPProvider

def make_w3(url: str, poa: bool, timeout: int) -> AsyncWeb3:
    """Create an AsyncWeb3 instance for *url*."""
    w3 = AsyncWeb3(AsyncHTTPProvider(url, request_kwargs={"timeout": timeout}))
    if poa:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3
