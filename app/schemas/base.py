from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,           # replaces orm_mode in Pydantic v2
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )