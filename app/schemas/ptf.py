from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field
import json

# PTF schemas
class PtfBase(BaseModel):
  name: str
  description: Optional[str] = None
  mission: Optional[str] = None
  vision: Optional[str] = None
  thumbnail_path: Optional[str] = None
  cover_path: Optional[str] = None
  website: Optional[str] = None
  email: Optional[str] = None
  phone: Optional[str] = None
  address: Optional[str] = None
  pays: Optional[str] = None
  date_creation: Optional[str] = None
  domaines: Optional[str] = None  # JSON string

  @computed_field
  @property
  def thumbnail_url(self) -> Optional[str]:
    """Constructs the full URL path for the thumbnail"""
    if self.thumbnail_path and self.thumbnail_path != "default.png":
      return f"https://api.plateforme-osci.org/static/{self.thumbnail_path}"
    return None

  @computed_field
  @property
  def cover_url(self) -> Optional[str]:
    """Constructs the full URL path for the cover image"""
    if self.cover_path:
      return f"http://localhost:8000/static/{self.cover_path}"
    return None

  @computed_field
  @property
  def domaines_list(self) -> List[str]:
    """Parse domaines JSON string to list"""
    if self.domaines:
      try:
        return json.loads(self.domaines)
      except:
        return []
    return []

class PtfCreate(PtfBase):
  pass

class PtfRead(PtfBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class PtfReadWithProjets(PtfBase):
  id: int
  projets: Optional[List["ProjetRead"]] = []
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class PtfUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  mission: Optional[str] = None
  vision: Optional[str] = None
  website: Optional[str] = None
  email: Optional[str] = None
  phone: Optional[str] = None
  address: Optional[str] = None
  pays: Optional[str] = None
  date_creation: Optional[str] = None
  domaines: Optional[str] = None  # JSON string

# Projet schemas
class ProjetBase(BaseModel):
  name: str
  ptf_id: Optional[int] = Field(default=None, foreign_key="ptf.id")

class ProjetCreate(ProjetBase):
  ptf: Optional[PtfRead] = None

class ProjetRead(ProjetBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class ProjetReadWithPtf(ProjetBase):
  id: int
  ptf: Optional[PtfRead] = None

class ProjetUpdate(BaseModel):
  name: Optional[str] = None
  ptf_id: Optional[int] = None