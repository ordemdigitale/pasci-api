from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class ContactMessageCreate(BaseModel):
    categorie_acteur: Optional[str] = None
    nom: str
    prenoms: str
    fonction: Optional[str] = None
    sexe: Optional[str] = None
    tranche_age: Optional[str] = None
    email: EmailStr
    contact: Optional[str] = None
    pays: Optional[str] = None
    lieu_residence: Optional[str] = None
    motif: str
    message: Optional[str] = None


class ContactMessageRead(BaseModel):
    id: int
    categorie_acteur: Optional[str] = None
    nom: str
    prenoms: str
    fonction: Optional[str] = None
    sexe: Optional[str] = None
    tranche_age: Optional[str] = None
    email: str
    contact: Optional[str] = None
    pays: Optional[str] = None
    lieu_residence: Optional[str] = None
    motif: str
    message: Optional[str] = None
    statut: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContactMessageUpdate(BaseModel):
    statut: Optional[str] = None
