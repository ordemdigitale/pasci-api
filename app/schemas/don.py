from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DonCreate(BaseModel):
    nom: str
    prenoms: Optional[str] = None
    fonction: Optional[str] = None
    sexe: Optional[str] = None
    tranche_age: Optional[str] = None
    email: str
    telephone: Optional[str] = None
    pays: Optional[str] = None
    lieu_residence: Optional[str] = None
    montant: int
    message: Optional[str] = None


class DonRead(BaseModel):
    id: int
    nom: str
    prenoms: Optional[str] = None
    fonction: Optional[str] = None
    sexe: Optional[str] = None
    tranche_age: Optional[str] = None
    email: str
    telephone: Optional[str] = None
    pays: Optional[str] = None
    lieu_residence: Optional[str] = None
    montant: int
    message: Optional[str] = None
    transaction_id: Optional[str] = None
    operateur: Optional[str] = None
    statut: str
    created_at: datetime

    class Config:
        from_attributes = True


# Legacy — kept for backward compat
class DonInitierResponse(BaseModel):
    don_id: int
    transaction_id: str
    payment_url: str
    simulated: bool


class WebhookPayload(BaseModel):
    transaction_id: Optional[str] = None
    cpm_trans_id: Optional[str] = None


# Paiement manuel
class DonSoumettreTransaction(BaseModel):
    transaction_id: str
    operateur: Optional[str] = None  # "wave" | "orange_money"


class DonCreateResponse(BaseModel):
    don_id: int
    statut: str
