# app/schemas/documentation.py | Documentation schemas
from __future__ import annotations

from pydantic import BaseModel, computed_field
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field

# Import at runtime for Pydantic model validation
from app.schemas.crasc import CrascRead, OscRead
from app.core.config import settings


class DocumentationBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "documentation"  # 'documentation' ou 'fiche'
    category: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    thumbnail_path: Optional[str] = None
    statut_publication: str = "publie"
    crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id")
    osc_id: Optional[int] = Field(default=None, foreign_key="osc.id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def file_url(self) -> Optional[str]:
        """Construit l'URL complète du fichier pour le frontend"""
        if self.file_path:
            # file_path already includes "documents/" prefix
            return f"{settings.API_BASE_URL}/static/{self.file_path}"
        return None

    @computed_field
    @property
    def thumbnail_url(self) -> str:
        """Construit l'URL complète de l'image de couverture pour le frontend"""
        return f"{settings.API_BASE_URL}/static/{self.thumbnail_path or 'default.png'}"


class DocumentationCreate(DocumentationBase):
    pass


class DocumentationRead(DocumentationBase):
    id: int
    slug: Optional[str] = None

    @computed_field
    @property
    def download_url(self) -> Optional[str]:
        """Construit l'URL de téléchargement du fichier"""
        if self.slug:
            return f"{settings.API_BASE_URL}/api/v1/documentation/{self.slug}/download"
        return None

    class Config:
        from_attributes = True


class DocumentationReadDetail(DocumentationBase):
    id: int
    slug: Optional[str] = None
    crasc: Optional[CrascRead] = None
    osc: Optional[OscRead] = None

    @computed_field
    @property
    def download_url(self) -> Optional[str]:
        """Construit l'URL de téléchargement du fichier"""
        if self.slug:
            return f"{settings.API_BASE_URL}/api/v1/documentation/{self.slug}/download"
        return None

    class Config:
        from_attributes = True


class DocumentationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    crasc_id: Optional[int] = None
    osc_id: Optional[int] = None
