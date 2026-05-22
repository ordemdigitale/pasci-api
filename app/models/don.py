from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, TEXT, Integer, func
from typing import Optional


class Don(SQLModel, table=True):
    __tablename__ = "don"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(max_length=100, nullable=False)
    prenoms: Optional[str] = Field(default=None, max_length=150)
    fonction: Optional[str] = Field(default=None, max_length=150)
    sexe: Optional[str] = Field(default=None, max_length=20)
    tranche_age: Optional[str] = Field(default=None, max_length=30)
    email: str = Field(max_length=200, nullable=False)
    telephone: Optional[str] = Field(default=None, max_length=50)
    pays: Optional[str] = Field(default=None, max_length=100)
    lieu_residence: Optional[str] = Field(default=None, max_length=150)
    montant: int = Field(nullable=False)  # en FCFA
    message: Optional[str] = Field(default=None, sa_column=Column(TEXT))

    # Paiement CinetPay
    transaction_id: Optional[str] = Field(default=None, max_length=100)
    notify_token: Optional[str] = Field(default=None, max_length=255)
    payment_url: Optional[str] = Field(default=None, max_length=500)
    statut: str = Field(default="en_attente", max_length=20)  # en_attente | success | failed

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    def __repr__(self) -> str:
        return f"<Don: {self.nom} — {self.montant} FCFA>"
