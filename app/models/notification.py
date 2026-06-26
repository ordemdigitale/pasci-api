from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, String, TEXT, func
from sqlmodel import Field, SQLModel


class Notification(SQLModel, table=True):
    """Notification interne affichée dans la cloche du tableau de bord."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True, nullable=False)
    title: str = Field(max_length=200, nullable=False)
    message: str = Field(sa_column=Column(TEXT, nullable=False))
    type: str = Field(default="info", max_length=50)
    link_url: Optional[str] = Field(default=None, max_length=500)
    is_read: bool = Field(default=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    read_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
