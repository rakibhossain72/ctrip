"""
General utility helper functions for the application.
"""
import datetime


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
    eth = float(wei_val) / 1e18
    if eth < 0.000001:
        return f"{eth:.4e}"
    if eth < 1:
        s = f"{eth:.8f}".rstrip("0").rstrip(".")
        return s if s else "0"
    s = f"{eth:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"
