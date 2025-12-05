from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class NewsCreate(BaseModel):
    title: str
    published_date: date
    image: Optional[str] = None


class NewsRead(NewsCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    published_date: Optional[date] = None

# Schemas for NewsArticle
class NewsArticleCreate(BaseModel):
    title: str
    content: str
#    preview_text: Optional[str] = None


class NewsArticleRead(NewsArticleCreate):
    article_id: UUID
    created_at: datetime
    updated_at: datetime