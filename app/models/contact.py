from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, TEXT, func
from typing import Optional


class ContactMessage(SQLModel, table=True):
    __tablename__ = "contact_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    categorie_acteur: Optional[str] = Field(default=None, max_length=100)
    nom: str = Field(max_length=100, nullable=False)
    prenoms: str = Field(max_length=150, nullable=False)
    fonction: Optional[str] = Field(default=None, max_length=150)
    sexe: Optional[str] = Field(default=None, max_length=20)
    tranche_age: Optional[str] = Field(default=None, max_length=30)
    email: str = Field(max_length=255, nullable=False)
    contact: Optional[str] = Field(default=None, max_length=30)
    pays: Optional[str] = Field(default=None, max_length=100)
    lieu_residence: Optional[str] = Field(default=None, max_length=150)
    motif: str = Field(max_length=100, nullable=False)
    message: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    statut: str = Field(default="nouveau", max_length=20)  # nouveau | lu | traite

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    def __repr__(self) -> str:
        return f"<Contact: {self.nom} {self.prenoms} — {self.motif}>"
