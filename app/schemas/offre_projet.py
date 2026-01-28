from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, computed_field
from uuid import UUID
import json

# Schemas for Offre Projet
class OffreProjetBase(BaseModel):
    nom: str
    osc: str
    domaine: str
    zone: str
    durée: str
    budget: str
    objectif: Optional[str] = None
    description: Optional[str] = None
    beneficiaires: Optional[str] = None
    statut: str = "En attente"
    progression: int = 0
    resultats_attendus: Optional[str] = None
    partenaires: Optional[str] = None
    image_path: Optional[str] = "default-project.jpg"
    date_publication: Optional[datetime] = None


class OffreProjetCreate(OffreProjetBase):
    pass


class OffreProjetRead(OffreProjetBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def image_url(self) -> Optional[str]:
        """Generate full URL for project image"""
        if self.image_path and self.image_path != "default-project.jpg":
            return f"http://localhost:8000/static/{self.image_path}"
        return None

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
    objectif: Optional[str] = None
    description: Optional[str] = None
    beneficiaires: Optional[str] = None
    statut: Optional[str] = None
    progression: Optional[int] = None
    resultats_attendus: Optional[str] = None
    partenaires: Optional[str] = None
    image_path: Optional[str] = None
    date_publication: Optional[datetime] = None
