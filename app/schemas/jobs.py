from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

# Schemas for News
class JobsBase(BaseModel):
    title: str
    employer: str
    description: str
    location: str
    type: str
    is_expired: bool = False
    publication_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class JobsCreate(JobsBase):
    pass


class JobsRead(JobsBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime


class JobsUpdate(BaseModel):
    title: Optional[str] = None
    employer: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    is_expired: Optional[bool] = False
    publication_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None