# app/models/numero_utile.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func
from typing import Optional


class NumeroUtile(SQLModel, table=True):
    __tablename__ = "numero_utile"

    id: Optional[int] = Field(default=None, primary_key=True)
    categorie: str = Field(max_length=100, nullable=False, description="Catégorie du numéro")
    label: str = Field(max_length=200, nullable=False, description="Nom du service")
    numero: str = Field(max_length=100, nullable=False, description="Numéro ou email")
    description: Optional[str] = Field(default=None, max_length=300, nullable=True)
    ordre: int = Field(default=0, nullable=False, description="Ordre d'affichage dans la catégorie")
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
        return f"<NumeroUtile: {self.label} — {self.numero}>"
