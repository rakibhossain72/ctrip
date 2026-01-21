from typing import Union

from fastapi import FastAPI
from api.health import heathh_router

app = FastAPI()

app.include_router(heathh_router)
def read_root():
    return {"Hello": "World"}
