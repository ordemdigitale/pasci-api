# models/adhesion.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, TEXT, func
from typing import Optional


class DemandeAdhesion(SQLModel, table=True):
    __tablename__ = "demande_adhesion"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom_organisation: str = Field(max_length=200, nullable=False)
    type_organisation: str = Field(max_length=100, nullable=False)
    region: str = Field(max_length=100, nullable=False)
    ville: Optional[str] = Field(default=None, max_length=100, nullable=True)
    email: str = Field(max_length=200, nullable=False)
    telephone: str = Field(max_length=50, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    motivation: str = Field(sa_column=Column(TEXT, nullable=False))
    statut: str = Field(default="en_attente", max_length=20, nullable=False)  # en_attente | approuvee | rejetee
    note_admin: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    def __repr__(self) -> str:
        return f"<DemandeAdhesion: {self.nom_organisation}>"
