# schemas/adhesion.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class DemandeAdhesionCreate(BaseModel):
    nom_organisation: str
    type_organisation: str
    crasc_nom: Optional[str] = None
    type_osc: Optional[str] = None
    region: str
    ville: Optional[str] = None
    email: str
    telephone: str
    description: Optional[str] = None
    motivation: str


class DemandeAdhesionRead(BaseModel):
    id: int
    nom_organisation: str
    type_organisation: str
    crasc_nom: Optional[str] = None
    type_osc: Optional[str] = None
    region: str
    ville: Optional[str] = None
    email: str
    telephone: str
    description: Optional[str] = None
    motivation: str
    statut: str
    note_admin: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DemandeAdhesionUpdate(BaseModel):
    statut: Optional[str] = None
    note_admin: Optional[str] = None


class OscCredentials(BaseModel):
    osc_id: int
    osc_name: str
    email: str
    username: str
    temp_password: str


class DemandeAdhesionReadWithCredentials(DemandeAdhesionRead):
    credentials: Optional[OscCredentials] = None
