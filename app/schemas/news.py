from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

# Schemas for News
class NewsCreate(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None


class NewsRead(NewsCreate):
    id: UUID
    preview_text: Optional[str]
    created_at: datetime
    updated_at: datetime


#class NewsUpdate(BaseModel):
#    title: Optional[str] = None
#    published_date: Optional[date] = None