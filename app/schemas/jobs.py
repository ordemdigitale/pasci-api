from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

# Schemas for News
class JobsCreate(BaseModel):
    title: str
    description: str
    location: str
    type: str
    is_expired: bool = False
    publication_date: Optional[datetime] = None # Check the None default handling later


class JobsRead(JobsCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


#class NewsUpdate(BaseModel):
#    title: Optional[str] = None
#    published_date: Optional[date] = None