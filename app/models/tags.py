# app/models/tags.py
"""
Tags/Categories model for News articles
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
import slugify


class NewsTag(SQLModel, table=True):
    """
    Association table for Many-to-Many relationship between News and Tags
    """
    __tablename__ = "news_tags"

    news_id: int = Field(foreign_key="news.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Tag(SQLModel, table=True):
    """
    Tag/Category model for categorizing news articles
    """
    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    slug: str = Field(max_length=120, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default="#3B82F6", max_length=7)  # Hex color code
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationship to News through association table
    news_items: List["News"] = Relationship(back_populates="tags", link_model=NewsTag)

    def __init__(self, **data):
        super().__init__(**data)
        if not self.slug and self.name:
            self.slug = slugify.slugify(self.name)
