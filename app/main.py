from typing import Union

from fastapi import FastAPI
from api.health import heathh_router

from blockchain.anvil import AnvilBlockchain

app = FastAPI()

app.include_router(heathh_router)

blockchain_anvil = AnvilBlockchain("http://localhost:8545")
@app.get("/")
def read_root():
    # return the balance of a sample address
    return {"balance": blockchain_anvil.get_balance("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")}