# models/hero_slide.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func
from typing import Optional


class HeroSlide(SQLModel, table=True):
    __tablename__ = "hero_slide"

    id: Optional[int] = Field(default=None, primary_key=True)
    image_path: str = Field(nullable=False, max_length=500)
    ordre: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    def __repr__(self) -> str:
        return f"<HeroSlide: {self.image_path}>"
