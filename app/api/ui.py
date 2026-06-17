from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/payment/{payment_id}", response_class=HTMLResponse)
async def payment_page(request: Request, payment_id: str):
    return templates.TemplateResponse("payment_page.html", {"request": request, "payment_id": payment_id})
