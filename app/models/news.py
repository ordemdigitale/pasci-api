from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
from sqlalchemy import Column, DateTime, func, String
from sqlmodel import SQLModel, Field


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