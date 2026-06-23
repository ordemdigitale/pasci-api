# models/annonce.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func
from typing import Optional


class Annonce(SQLModel, table=True):
    __tablename__ = "annonce"

    id: Optional[int] = Field(default=None, primary_key=True)
    texte: str = Field(nullable=False, max_length=500)
    is_active: bool = Field(default=True)
    ordre: int = Field(default=0)
    date_fin: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    def __repr__(self) -> str:
        return f"<Annonce: {self.texte[:50]}>"
