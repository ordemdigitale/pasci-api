# models/journal.py | Historique des actions réalisées dans le back-office
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, TEXT, func
from sqlmodel import Field, SQLModel


class JournalAction(SQLModel, table=True):
    """Trace d'une action décisive : qui a fait quoi, sur quoi et quand.

    L'utilisateur est conservé sous forme de texte en plus de la clé
    étrangère : la suppression d'un compte ne doit pas effacer la trace de
    ce qu'il a validé ou rejeté.
    """

    __tablename__ = "journal_action"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="SET NULL", index=True)
    utilisateur: Optional[str] = Field(default=None, max_length=255)
    action: str = Field(max_length=60, nullable=False, index=True)
    cible_type: Optional[str] = Field(default=None, max_length=50, index=True)
    cible_id: Optional[str] = Field(default=None, max_length=100)
    cible_libelle: Optional[str] = Field(default=None, max_length=300)
    details: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )

    def __repr__(self) -> str:
        return f"<Journal: {self.action} par {self.utilisateur}>"
