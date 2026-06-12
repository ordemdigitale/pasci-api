from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, TEXT, func
from sqlmodel import Field, SQLModel


class Faq(SQLModel, table=True):
    __tablename__ = "faq"

    id: Optional[int] = Field(default=None, primary_key=True)
    question: str = Field(max_length=300, nullable=False, description="Question")
    answer: str = Field(sa_column=Column(TEXT, nullable=False), description="Réponse")
    ordre: int = Field(default=0, nullable=False, description="Ordre d'affichage")
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    def __repr__(self) -> str:
        return f"<Faq: {self.question}>"
