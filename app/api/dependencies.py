from fastapi import Request
from blockchain.base import BlockchainBase
from utils.crypto import HDWalletManager

def get_blockchains(request: Request) -> dict[str, BlockchainBase]:
    blockchains = request.app.state.blockchains
    if blockchains is None:
        raise RuntimeError("Blockchain not initialized in lifespan")
    return blockchains

def get_hdwallet(request: Request ) -> HDWalletManager:
    hdwallet = request.app.state.hdwallet
    if hdwallet is None:
        raise RuntimeError("HDWallet manager not initialized in lifespan")
    return hdwallet