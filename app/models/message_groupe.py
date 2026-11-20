# models/message_groupe.py | Messages envoyés à un ensemble de destinataires
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, TEXT, func
from sqlmodel import Field, SQLModel


class MessageGroupe(SQLModel, table=True):
    """Message adressé à une sélection d'OSC ou de PTF.

    Conservé pour l'historique : objet, contenu, critères de sélection et
    nombre de destinataires réellement touchés.
    """

    __tablename__ = "message_groupe"

    id: Optional[int] = Field(default=None, primary_key=True)
    objet: str = Field(max_length=200, nullable=False)
    message: str = Field(sa_column=Column(TEXT, nullable=False))
    # Critères de sélection sérialisés en JSON (CRASC, type, catégorie, région,
    # pôle, task force) : permet de rejouer ou d'auditer un envoi.
    criteres: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    lien: Optional[str] = Field(default=None, max_length=500)

    nb_destinataires: int = Field(default=0)
    nb_emails: int = Field(default=0)
    nb_notifications: int = Field(default=0)

    auteur_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    auteur_nom: Optional[str] = Field(default=None, max_length=255)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )

    def __repr__(self) -> str:
        return f"<Message groupé: {self.objet}>"
