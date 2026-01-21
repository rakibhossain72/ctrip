from fastapi import APIRouter


heathh_router = APIRouter()
@heathh_router.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}