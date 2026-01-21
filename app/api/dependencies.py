# dependencies.py    ← create this file in app/ or app/api/
from fastapi import Depends, Request
from blockchain.anvil import AnvilBlockchain
from utils.crypto import HDWalletManager

def get_anvil(request: Request) -> AnvilBlockchain:
    anvil = request.app.state.anvil
    if anvil is None:
        raise RuntimeError("Anvil client not initialized in lifespan")
    return anvil

def get_hdwallet(request: Request ) -> HDWalletManager:
    hdwallet = request.app.state.hdwallet
    if hdwallet is None:
        raise RuntimeError("HDWallet manager not initialized in lifespan")
    return hdwallet