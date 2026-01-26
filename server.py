from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.health import health_router
from app.api.v1.payments import router as payments_router
from app.utils.crypto import HDWalletManager
from app.blockchain.anvil import AnvilBlockchain
from app.db.base import Base
from app.db.engine import engine
from app.db.session import SessionLocal
from app.db.seed import add_chain_states




from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    from app.blockchain.manager import get_blockchains
    app.state.blockchains = get_blockchains()
    
    hdwallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)
    app.state.hdwallet = hdwallet

    Base.metadata.create_all(bind=engine)

    add_chain_states(SessionLocal(), app.state.blockchains)

    # Trigger background workers via Dramatiq
    from app.workers.listener import listen_for_payments
    from app.workers.sweeper import sweep_payments
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