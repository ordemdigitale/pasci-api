from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
from sqlalchemy import Column, DateTime, String, func
from sqlmodel import SQLModel, Field
from app.utils.preview_text_generator import generate_excerpt


class NewsBase(SQLModel):
  title: str
  published_date: date
  image: Optional[str] = Field(default=None, max_length=2048, description="ImageKit public URL")


class News(NewsBase, table=True):
  # Use UUID primary key to avoid integer auto-increment reliance
  id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)

  # Timestamps
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now()),
  )

  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(
      DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()
    ),
  )

  # Optional: Nice representation in admin/logs
  def __repr__(self) -> str:
      return f"<News {self.id}: {self.title} ({self.published_date})>"
  

class NewsArticle(SQLModel, table=True):
   """ Represents a news article in the database. """
   article_id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, description="Unique news article identifier")
   title: str = Field(max_length=250, nullable=False, description="Title of the news article")
   content: str = Field(sa_column=Column(String, nullable=True), description="Content of the news article")
   preview_text: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True), description="Preview text of the article")

   # Timestamps
   created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc),
      sa_column=Column(DateTime(timezone=True), server_default=func.now()),
   )

   updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )
   
   # Representation in admin/logs
   def __repr__(self) -> str:
      return f"<NewsArticle {self.article_id}: {self.title}>"