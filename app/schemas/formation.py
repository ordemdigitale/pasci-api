# app/schemas/formation.py
"""
Pydantic schemas for Formation model
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, computed_field
from app.core.config import settings


# ── Rubrique ──────────────────────────────────────────────────

class FormationRubriqueCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#E05017"
    is_active: bool = True


class FormationRubriqueRead(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FormationRubriqueUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


# ── Inscription ────────────────────────────────────────────────

class FormationInscriptionCreate(BaseModel):
    participant_name: str
    participant_email: str


class FormationInscriptionRead(BaseModel):
    id: int
    formation_id: int
    user_id: Optional[UUID] = None
    participant_name: str
    participant_email: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    certificate_issued: bool
    # Paiement
    payment_status: str
    payment_transaction_id: Optional[str] = None
    payment_amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_operator: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FormationAvisCreate(BaseModel):
    note: int = Field(ge=1, le=5)
    commentaire: Optional[str] = None


class FormationAvisRead(BaseModel):
    id: int
    formation_id: int
    participant_name: str
    note: int
    commentaire: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaiementInitierResponse(BaseModel):
    """Réponse lors de l'initiation d'un paiement CinetPay"""
    inscription_id: int
    payment_url: str
    transaction_id: str
    amount: float
    currency: str
    cinetpay_configured: bool  # False = mode simulation (pas encore d'API)


class PaiementWebhookPayload(BaseModel):
    """Payload reçu par CinetPay après paiement"""
    cpm_trans_id: str
    cpm_site_id: str
    cpm_amount: str
    cpm_currency: str
    cpm_payid: str
    cpm_payment_date: Optional[str] = None
    cpm_payment_time: Optional[str] = None
    cpm_error_message: Optional[str] = None
    cpm_result: str        # "00" = succès
    cpm_trans_status: str  # "ACCEPTED" | "REFUSED" | "PENDING"
    payment_method: Optional[str] = None


# ── Certificat ─────────────────────────────────────────────────

class CertificatRead(BaseModel):
    id: int
    code: str
    inscription_id: int
    formation_title: str
    participant_name: str
    participant_email: str
    issued_at: datetime

    class Config:
        from_attributes = True


class FormationBase(BaseModel):
    """Base Formation schema"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    trainer: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    registration_link: Optional[str] = Field(None, max_length=500)
    materials_link: Optional[str] = Field(None, max_length=500)
    is_published: bool = False
    type: str = Field(default="gratuite")  # "gratuite" ou "payante"
    price: Optional[float] = None
    rubrique_id: Optional[int] = None


class FormationCreate(FormationBase):
    """Schema for creating a formation"""
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None


class FormationUpdate(BaseModel):
    """Schema for updating a formation"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    trainer: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    current_participants: Optional[int] = Field(None, ge=0)
    registration_link: Optional[str] = Field(None, max_length=500)
    materials_link: Optional[str] = Field(None, max_length=500)
    is_published: Optional[bool] = None
    is_full: Optional[bool] = None
    is_completed: Optional[bool] = None
    type: Optional[str] = None
    price: Optional[float] = None
    rubrique_id: Optional[int] = None
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None


class FormationRead(FormationBase):
    """Schema for reading a formation"""
    id: int
    slug: str
    current_participants: int
    is_full: bool
    is_completed: bool
    thumbnail_path: str
    rubrique_id: Optional[int] = None
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def thumbnail_url(self) -> str:
        """Generate full URL for thumbnail image"""
        if self.thumbnail_path and self.thumbnail_path != "default.png":
            return f"http://localhost:8000/static/{self.thumbnail_path}"
        return "http://localhost:8000/static/default.png"

    class Config:
        from_attributes = True


class CrascSimple(BaseModel):
    """Simple CRASC schema for relations"""
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True


class OscSimple(BaseModel):
    """Simple OSC schema for relations"""
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True


# ── Modules & Leçons ───────────────────────────────────────────

class FormationLeconCreate(BaseModel):
    title: str
    type: str = "text"  # "video" | "pdf" | "text"
    content: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_preview: bool = False
    order: int = 0


class FormationLeconUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_preview: Optional[bool] = None
    order: Optional[int] = None


class FormationLeconRead(BaseModel):
    id: int
    module_id: int
    title: str
    type: str
    content: Optional[str] = None
    file_path: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_preview: bool
    order: int
    created_at: datetime

    @computed_field
    @property
    def file_url(self) -> Optional[str]:
        if self.file_path:
            return f"{settings.API_BASE_URL}/static/{self.file_path}"
        return None

    class Config:
        from_attributes = True


class FormationModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order: int = 0


class FormationModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class FormationModuleRead(BaseModel):
    id: int
    formation_id: int
    title: str
    description: Optional[str] = None
    order: int
    lecons: List[FormationLeconRead] = []
    created_at: datetime

    class Config:
        from_attributes = True


class FormationReadWithRelations(FormationRead):
    """Formation with CRASC, OSC and Rubrique details"""
    rubrique: Optional[FormationRubriqueRead] = None
    crasc: Optional[CrascSimple] = None
    osc: Optional[OscSimple] = None
