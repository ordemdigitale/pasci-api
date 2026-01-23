# app/schemas/tags.py
"""
Pydantic schemas for Tag model
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """Base Tag schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field("#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    """Schema for creating a tag"""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class TagRead(TagBase):
    """Schema for reading a tag"""
    id: int
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True


class TagWithNewsCount(TagRead):
    """Tag with count of associated news articles"""
    news_count: int = 0
