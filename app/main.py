# main.py
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from api.health import health_router
from api.v1.payments import router as payments_router
from utils.crypto import HDWalletManager
from blockchain.anvil import AnvilBlockchain
from db.base import Base
from db.engine import engine
from db.session import SessionLocal
from db.seed import add_chain_states




from core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    from blockchain.manager import get_blockchains
    app.state.blockchains = get_blockchains()
    
    hdwallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)
    app.state.hdwallet = hdwallet

    Base.metadata.create_all(bind=engine)

    add_chain_states(SessionLocal(), app.state.blockchains)

    # Trigger background workers via Dramatiq
    from workers.listener import listen_for_payments
    from workers.sweeper import sweep_payments
    listen_for_payments.send()
    sweep_payments.send()

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(payments_router)


    

@app.get("/")
def read_root():
    anvil: AnvilBlockchain = app.state.anvil
    balance = anvil.get_balance("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
    return {"balance": balance}