"""
Base Pydantic schemas for the application.
"""
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration for all Pydantic models."""
    model_config = ConfigDict(
        from_attributes=True,           # replaces orm_mode in Pydantic v2
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )
