from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class JournalActionRead(BaseModel):
    id: int
    user_id: Optional[UUID] = None
    utilisateur: Optional[str] = None
    action: str
    # Renseigné à la lecture depuis le référentiel des actions
    action_libelle: str = ""
    cible_type: Optional[str] = None
    cible_id: Optional[str] = None
    cible_libelle: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JournalPage(BaseModel):
    items: List[JournalActionRead]
    total: int
    page: int
    size: int
    pages: int


class ActionReferentiel(BaseModel):
    code: str
    libelle: str
