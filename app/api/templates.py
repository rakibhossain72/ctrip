"""
Shared Jinja2 template environment for the FastAPI app.

Centralizes the template directory, rendering helpers, and template filters so
both the public UI (``app.api.ui``) and the admin console
(``app.api.admin_ui``) render consistently.
"""
from __future__ import annotations

from datetime import datetime

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def fmt_dt(iso: str | None, full: bool = False) -> str:
    """Format an ISO-8601 timestamp like the React admin console did."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso
    if full:
        return dt.strftime("%b %d, %Y, %I:%M %p")
    return dt.strftime("%b %d, %I:%M %p")


def fmt_amount(value) -> str:
    """Thousands-separate integer values, pass through decimal strings."""
    if value is None:
        return "—"
    s = str(value)
    if "." in s:
        return s
    try:
        return format(int(s), ",")
    except (TypeError, ValueError):
        return s


def fmt_int(value) -> str:
    try:
        return format(int(value or 0), ",")
    except (TypeError, ValueError):
        return str(value or 0)


def badge_class(status: str) -> str:
    """Bootstrap-style badge variant for a payment status."""
    mapping = {
        "pending": "badge-warning",
        "detected": "badge-outline",
        "confirmed": "badge-success",
        "paid": "badge-success",
        "settled": "badge-success",
        "expired": "badge-destructive",
        "failed": "badge-destructive",
    }
    return mapping.get(status, "badge-secondary")


templates.env.filters["fmt_dt"] = fmt_dt
templates.env.filters["fmt_dt_full"] = lambda iso: fmt_dt(iso, full=True)
templates.env.filters["fmt_amount"] = fmt_amount
templates.env.filters["fmt_int"] = fmt_int
templates.env.filters["badge"] = badge_class
