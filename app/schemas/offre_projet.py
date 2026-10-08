from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, computed_field
from uuid import UUID
from app.core.config import settings
import json


class PtfMinimal(BaseModel):
    """Infos PTF minimales pour l'embed dans OffreProjetRead"""
    id: int
    name: str
    slug: Optional[str] = None
    thumbnail_url: Optional[str] = None
    pays: Optional[str] = None

    class Config:
        from_attributes = True


# Schemas for Offre Projet
class OffreProjetBase(BaseModel):
    nom: str
    osc: str
    domaine: str
    zone: str
    durée: str
    budget: str
    offre_url: Optional[str] = None
    objectif: Optional[str] = None
    description: Optional[str] = None
    beneficiaires: Optional[str] = None
    statut: str = "En attente"
    progression: int = 0
    resultats_attendus: Optional[str] = None
    partenaires: Optional[str] = None
    image_path: Optional[str] = "default-project.jpg"
    date_publication: Optional[datetime] = None
    date_limite_soumission: Optional[datetime] = None
    ptf_id: Optional[int] = None


class OffreProjetCreate(OffreProjetBase):
    pass


class OffreProjetRead(OffreProjetBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime
    ptf: Optional[PtfMinimal] = None

    @computed_field
    @property
    def image_url(self) -> Optional[str]:
        """Generate full URL for project image"""
        if self.image_path and self.image_path != "default-project.jpg":
            return f"{settings.API_BASE_URL}/static/{self.image_path}"
        return None

    @computed_field
    @property
    def soumission_ouverte(self) -> bool:
        """Vrai tant que la date limite de soumission n'est pas dépassée (ou s'il n'y en a pas)."""
        if not self.date_limite_soumission:
            return True
        fin = self.date_limite_soumission
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        return fin >= datetime.now(timezone.utc)

    @computed_field
    @property
    def jours_restants(self) -> Optional[int]:
        """Jours avant la date limite (0 le dernier jour), None sans date ou si elle est passée."""
        if not self.date_limite_soumission or not self.soumission_ouverte:
            return None
        fin = self.date_limite_soumission
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        return max(0, (fin - datetime.now(timezone.utc)).days)

    @computed_field
    @property
    def resultats_attendus_list(self) -> List[str]:
        """Parse resultats_attendus JSON to list"""
        if self.resultats_attendus:
            try:
                return json.loads(self.resultats_attendus)
            except:
                return []
        return []

    @computed_field
    @property
    def partenaires_list(self) -> List[str]:
        """Parse partenaires JSON to list"""
        if self.partenaires:
            try:
                return json.loads(self.partenaires)
            except:
                return []
        return []


class OffreProjetUpdate(BaseModel):
    nom: Optional[str] = None
    osc: Optional[str] = None
    domaine: Optional[str] = None
    zone: Optional[str] = None
    durée: Optional[str] = None
    budget: Optional[str] = None
    offre_url: Optional[str] = None
    objectif: Optional[str] = None
    description: Optional[str] = None
    beneficiaires: Optional[str] = None
    statut: Optional[str] = None
    progression: Optional[int] = None
    resultats_attendus: Optional[str] = None
    partenaires: Optional[str] = None
    image_path: Optional[str] = None
    date_publication: Optional[datetime] = None
    date_limite_soumission: Optional[datetime] = None
    ptf_id: Optional[int] = None
