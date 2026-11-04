from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, TEXT, func
from typing import Optional
from uuid import UUID


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


class ContactReponse(SQLModel, table=True):
    """Réponse envoyée depuis le backoffice à un message de contact.

    Historisée pour garder la trace de ce qui a été répondu, par qui et quand :
    plusieurs réponses sont possibles sur un même message.
    """

    __tablename__ = "contact_reponse"

    id: Optional[int] = Field(default=None, primary_key=True)
    contact_id: int = Field(foreign_key="contact_message.id", ondelete="CASCADE", index=True)
    message: str = Field(sa_column=Column(TEXT, nullable=False))
    auteur_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    auteur_nom: Optional[str] = Field(default=None, max_length=200)
    auteur_email: Optional[str] = Field(default=None, max_length=255)
    envoye: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    def __repr__(self) -> str:
        return f"<ContactReponse: message #{self.contact_id}>"
