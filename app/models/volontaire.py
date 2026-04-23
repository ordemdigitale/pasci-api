from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, TEXT, func
from typing import Optional


class Volontaire(SQLModel, table=True):
    __tablename__ = "volontaire"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(max_length=200, nullable=False)
    email: str = Field(max_length=200, nullable=False)
    telephone: Optional[str] = Field(default=None, max_length=50)
    profession: Optional[str] = Field(default=None, max_length=200)
    domaine: str = Field(max_length=200, nullable=False)
    disponibilite: Optional[str] = Field(default=None, max_length=50)
    motivation: str = Field(sa_column=Column(TEXT, nullable=False))
    statut: str = Field(default="en_attente", max_length=20)  # en_attente | contacte | accepte | rejete
    note_admin: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    def __repr__(self) -> str:
        return f"<Volontaire: {self.nom} — {self.domaine}>"
