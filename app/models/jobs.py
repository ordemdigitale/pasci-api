# models/jobs.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, func
from typing import Optional
from uuid import uuid4, UUID

class Jobs(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(max_length=200, nullable=False, description="Job title")
    description: str = Field(sa_column=Column(String, nullable=True), description="Job description")
    location: str = Field(max_length=100, nullable=False, description="Job location")
    type: str = Field(max_length=200, nullable=False, description="Job type")
    is_expired: bool = Field(default=False, description="Indicates if the job posting is expired")
    # Publication date that defaults to now if not provided
    publication_date: Optional[datetime] = Field(
       default_factory=lambda: datetime.now(timezone.utc),
       sa_column=Column(DateTime(timezone=True), server_default=func.now()),
       description="Date when the job was published")
    # Timestamps (auto-managed)
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
      return f"<Poste: {self.title}>"