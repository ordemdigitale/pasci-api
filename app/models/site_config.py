# models/site_config.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, TEXT, func
from typing import Optional


class SiteConfig(SQLModel, table=True):
    __tablename__ = "site_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(nullable=False, max_length=100, unique=True)
    value: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )

    def __repr__(self) -> str:
        return f"<SiteConfig: {self.key}>"
