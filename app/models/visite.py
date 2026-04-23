from datetime import datetime, timezone, date
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, Date, String, func
from typing import Optional


class Visite(SQLModel, table=True):
    __tablename__ = "visite"

    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(max_length=500, nullable=False)
    ip_hash: str = Field(max_length=64, nullable=False)   # SHA256 tronqué — pas de données perso
    date_visite: date = Field(sa_column=Column(Date, nullable=False))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
