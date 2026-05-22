from pydantic import BaseModel, computed_field, field_validator
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from math import isnan
from sqlmodel import Field
from app.core.config import settings

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
  items: List[T]
  total: int
  page: int
  size: int
  pages: int


# CRASC Schemas
class CrascBase(BaseModel):
  name: str
  description: Optional[str] = None
  osc_count: Optional[int] = 0

class CrascCreate(CrascBase):
  pass

class CrascRead(CrascBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class CrascReadDetail(CrascBase):
  id: int
  slug: Optional[str] = None
  oscs: Optional[List["OscRead"]] = []
  regions: Optional[List["RegionRead"]] = []
  news: Optional[List["NewsRead"]] = []
  evenements: Optional[List["EvenementRead"]] = []
  videos: Optional[List["CrascVideoRead"]] = []
  class Config:
    from_attributes = True

class CrascUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  osc_count: Optional[int] = None


#Region Schemas
class RegionBase(BaseModel):
  name: str
  crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id")

class RegionCreate(RegionBase):
  pass

class RegionRead(RegionBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class RegionReadDetail(RegionBase):
  id: int
  slug: Optional[str] = None
  crasc: Optional["CrascRead"]
  class Config:
    from_attributes = True

class RegionUpdate(BaseModel):
  name: Optional[str] = None
  crasc_id: Optional[int] = None


#OscType Schemas
class OscTypeBase(BaseModel):
  name: str
  description: Optional[str] = None

class OscTypeCreate(OscTypeBase):
  pass

class OscTypeRead(OscTypeBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class OscTypeReadDetail(OscTypeBase):
  id: int
  slug: Optional[str] = None
  oscs: Optional[list["OscRead"]] = []
  class Config:
    from_attributes = True

class OscTypeUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None


#Osc Schemas
class OscBase(BaseModel):
  name: str
  description: Optional[str] = None
  thumbnail_path: Optional[str] = None
  type_id: Optional[int] = Field(default=None, foreign_key="osctype.id")
  crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id")
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None
  # Informations de contact pour l'annuaire
  email: Optional[str] = None
  phone: Optional[str] = None
  ville: Optional[str] = None
  # Champs complémentaires
  website: Optional[str] = None
  reseaux_sociaux: Optional[str] = None
  date_creation: Optional[str] = None
  numero_recepisse: Optional[str] = None
  niveau_couverture: Optional[str] = None
  zone_couverture: Optional[str] = None
  categorie: Optional[str] = None
  domaine_prioritaire: Optional[str] = None
  domaine_prioritaire_2: Optional[str] = None
  domaine_prioritaire_3: Optional[str] = None
  domaine_prioritaire_4: Optional[str] = None
  nb_membres: Optional[int] = None
  nb_femmes_membres: Optional[int] = None
  nb_membres_jeunes: Optional[int] = None
  nb_membres_be: Optional[int] = None
  nb_personnes_engagees: Optional[int] = None
  nb_beneficiaires: Optional[int] = None
  nb_activites: Optional[int] = None
  budget_annuel: Optional[int] = None
  type_financement: Optional[str] = None
  etat_cotisations: Optional[str] = None
  montant_cotisation: Optional[int] = None
  nom_president: Optional[str] = None
  sexe_president: Optional[str] = None
  mode_designation_president: Optional[str] = None
  duree_mandat_be: Optional[str] = None
  adhesion_crasc: Optional[bool] = None
  reseau_appartenance: Optional[str] = None
  secteurs_activites: Optional[str] = None
  populations_cibles: Optional[str] = None
  savoir_faire: Optional[str] = None
  difficultes: Optional[str] = None
  recommandations: Optional[str] = None
  financement_cotisation: Optional[bool] = None
  financement_dons: Optional[bool] = None
  financement_legs: Optional[bool] = None
  financement_collectivites: Optional[bool] = None
  financement_fonds_propres: Optional[bool] = None
  financement_ong_intl: Optional[bool] = None
  financement_multilateral: Optional[bool] = None
  
  @field_validator("latitude", "longitude", mode="before")
  @classmethod
  def sanitize_float(cls, v):
    if v is None:
      return None
    try:
      if isnan(float(v)):
        return None
    except (TypeError, ValueError):
      return None
    return v

  @computed_field
  @property
  def thumbnail_url(self) -> Optional[str]:
    """Constructs the full URL path for the thumbnail"""
    if self.thumbnail_path and self.thumbnail_path != "default.png":
      return f"{settings.API_BASE_URL}/static/{self.thumbnail_path}"
    return None

class OscCreate(OscBase):
  pass

class PoleMinimal(BaseModel):
  id: int
  name: str
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class OscRead(OscBase):
  id: int
  slug: Optional[str] = None
  poles: Optional[List[PoleMinimal]] = []
  class Config:
    from_attributes = True

class OscReadDetail(OscBase):
  id: int
  slug: Optional[str] = None
  type: Optional[OscTypeRead] = None
  crasc: Optional[CrascRead] = None
  news_items: Optional[List["NewsRead"]] = []
  poles: Optional[List[PoleMinimal]] = []
  class Config:
    from_attributes = True
    
class OscUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  type_id: Optional[int] = None
  crasc_id: Optional[int] = None
  address: Optional[str] = None
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  email: Optional[str] = None
  phone: Optional[str] = None
  ville: Optional[str] = None
  website: Optional[str] = None
  reseaux_sociaux: Optional[str] = None
  date_creation: Optional[str] = None
  numero_recepisse: Optional[str] = None
  niveau_couverture: Optional[str] = None
  zone_couverture: Optional[str] = None
  categorie: Optional[str] = None
  domaine_prioritaire: Optional[str] = None
  domaine_prioritaire_2: Optional[str] = None
  domaine_prioritaire_3: Optional[str] = None
  domaine_prioritaire_4: Optional[str] = None
  nb_membres: Optional[int] = None
  nb_femmes_membres: Optional[int] = None
  nb_membres_jeunes: Optional[int] = None
  nb_membres_be: Optional[int] = None
  nb_personnes_engagees: Optional[int] = None
  nb_beneficiaires: Optional[int] = None
  nb_activites: Optional[int] = None
  budget_annuel: Optional[int] = None
  type_financement: Optional[str] = None
  etat_cotisations: Optional[str] = None
  montant_cotisation: Optional[int] = None
  nom_president: Optional[str] = None
  sexe_president: Optional[str] = None
  mode_designation_president: Optional[str] = None
  duree_mandat_be: Optional[str] = None
  adhesion_crasc: Optional[bool] = None
  reseau_appartenance: Optional[str] = None
  secteurs_activites: Optional[str] = None
  populations_cibles: Optional[str] = None
  savoir_faire: Optional[str] = None
  difficultes: Optional[str] = None
  recommandations: Optional[str] = None


#News Schemas
class NewsBase(BaseModel):
  title: str
  content: Optional[str] = None
  thumbnail_path: Optional[str] = None
  created_at: Optional[datetime] = None
  updated_at: Optional[datetime] = None
  # IDs are optional in the base so they can be omitted in Create/Read if needed
  osc_id: Optional[int] = Field(default=None, foreign_key="osc.id")
  crasc_id: Optional[int] = Field(default=None, foreign_key="crascregion.id")
  @computed_field
  @property
  def thumbnail_url(self) -> str:
    """Constructs the full URL path for the frontend"""
    return f"{settings.API_BASE_URL}/static/{self.thumbnail_path}"

class NewsCreate(NewsBase):
    pass

class NewsRead(NewsBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class NewsReadDetail(NewsBase):
  id: int
  slug: Optional[str] = None
  crasc: Optional[CrascRead] = None
  osc: Optional[OscRead] = None
  class Config:
    from_attributes = True

class NewsUpdate(BaseModel):
  title: Optional[str] = None
  content: Optional[str] = None
  osc_id: Optional[int] = None
  crasc_id: Optional[int] = None


# CrascVideo Schemas
class CrascVideoCreate(BaseModel):
  crasc_id: int
  titre: str
  url: str
  description: Optional[str] = None
  ordre: int = 0

class CrascVideoRead(BaseModel):
  id: int
  crasc_id: int
  titre: str
  url: str
  description: Optional[str] = None
  ordre: int = 0
  created_at: Optional[datetime] = None
  class Config:
    from_attributes = True


# Evenement Schemas
class EvenementBase(BaseModel):
  title: str
  description: Optional[str] = None
  date_debut: datetime
  date_fin: Optional[datetime] = None
  lieu: Optional[str] = None
  crasc_id: Optional[int] = None

class EvenementCreate(EvenementBase):
  pass

class EvenementRead(EvenementBase):
  id: int
  created_at: Optional[datetime] = None
  class Config:
    from_attributes = True

class EvenementUpdate(BaseModel):
  title: Optional[str] = None
  description: Optional[str] = None
  date_debut: Optional[datetime] = None
  date_fin: Optional[datetime] = None
  lieu: Optional[str] = None