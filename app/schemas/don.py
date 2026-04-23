from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class DonCreate(BaseModel):
    nom: str
    email: str
    telephone: Optional[str] = None
    montant: int
    message: Optional[str] = None


class DonRead(BaseModel):
    id: int
    nom: str
    email: str
    telephone: Optional[str] = None
    montant: int
    message: Optional[str] = None
    transaction_id: Optional[str] = None
    statut: str
    created_at: datetime

    class Config:
        from_attributes = True


class DonInitierResponse(BaseModel):
    don_id: int
    transaction_id: str
    payment_url: str
    simulated: bool


class WebhookPayload(BaseModel):
    transaction_id: Optional[str] = None
    cpm_trans_id: Optional[str] = None
