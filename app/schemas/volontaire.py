from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VolontaireCreate(BaseModel):
    nom: str
    email: str
    telephone: Optional[str] = None
    profession: Optional[str] = None
    domaine: str
    disponibilite: Optional[str] = None
    motivation: str


class VolontaireRead(BaseModel):
    id: int
    nom: str
    email: str
    telephone: Optional[str] = None
    profession: Optional[str] = None
    domaine: str
    disponibilite: Optional[str] = None
    motivation: str
    statut: str
    note_admin: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VolontaireUpdate(BaseModel):
    statut: Optional[str] = None
    note_admin: Optional[str] = None
