from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/")
async def admin_redirect():
    return RedirectResponse(url="/admin/dashboard")

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@router.get("/admin/payments/{payment_id}", response_class=HTMLResponse)
async def admin_payment_detail(request: Request, payment_id: str):
    return templates.TemplateResponse("admin_payment_detail.html", {"request": request, "payment_id": payment_id})

@router.get("/payment/{payment_id}", response_class=HTMLResponse)
async def payment_page(request: Request, payment_id: str):
    return templates.TemplateResponse("payment_page.html", {"request": request, "payment_id": payment_id})
