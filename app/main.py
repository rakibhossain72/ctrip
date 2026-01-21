# main.py
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from api.health import health_router
from utils.crypto import HDWalletManager
from blockchain.anvil import AnvilBlockchain



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    anvil = AnvilBlockchain("http://localhost:8545")
    hdwallet = HDWalletManager(mnemonic_phrase="test test test test test test test test test test test junk")
    app.state.anvil = anvil
    app.state.hdwallet = hdwallet

    yield
    
    print("Anvil client closed")


app = FastAPI(lifespan=lifespan)
app.include_router(health_router)


@app.get("/")
def read_root():
    anvil: AnvilBlockchain = app.state.anvil
    balance = anvil.get_balance("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
    return {"balance": balance}