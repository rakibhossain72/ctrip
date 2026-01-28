"""
Shared utilities for background workers.
"""
from app.core.config import settings


def get_enabled_chains():
    """
    Returns a list of chain names to process.
    Falls back to ['anvil'] if no chains are configured.
    """
    chains = [c["name"] for c in settings.chains]
    if not chains:
        return ["anvil"]
    return chains
