"""
General utility helper functions for the application.
"""
import datetime
from decimal import Decimal

def iso_date(dt: datetime.datetime) -> str:
    """Format a datetime to ISO date string (YYYY-MM-DD)."""
    return dt.strftime("%Y-%m-%d")


def now_utc() -> datetime.datetime:
    """Return timezone-naive current UTC datetime."""
    return datetime.datetime.utcnow()


def wei_to_eth_str(wei_val) -> str:
    """Convert Wei (or token base unit) to human readable string."""
    if not wei_val:
        return "0"
    try:
        dec_val = Decimal(str(wei_val))
    except Exception:
        dec_val = Decimal(wei_val)
    eth = dec_val / Decimal("1000000000000000000")
    s = f"{eth:.18f}".rstrip("0").rstrip(".")
    return s if s else "0"
