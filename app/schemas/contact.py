from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


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


class ContactReponseCreate(BaseModel):
    """Réponse rédigée depuis le backoffice et envoyée par email à l'usager."""

    message: str = Field(min_length=1)
    # Adresse à laquelle l'usager répondra (par défaut celle de l'administrateur)
    reply_to: Optional[EmailStr] = None


class ContactReponseRead(BaseModel):
    id: int
    contact_id: int
    message: str
    auteur_id: Optional[UUID] = None
    auteur_nom: Optional[str] = None
    auteur_email: Optional[str] = None
    envoye: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ContactMessageDetail(ContactMessageRead):
    """Message de contact avec l'historique des réponses envoyées."""

    reponses: List[ContactReponseRead] = []


class ContactEmailsRead(BaseModel):
    """Boîtes mails qui reçoivent les notifications de nouveaux messages."""

    emails: List[str] = []


class ContactEmailsUpdate(BaseModel):
    emails: List[str] = []
