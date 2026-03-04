from pydantic import BaseModel, Field
from datetime import datetime


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=63, pattern=r"^[a-z0-9-]+$")


class Organization(BaseModel):
    id: str
    name: str
    slug: str


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    api_key: str  # only shown once on creation
    created_at: datetime
