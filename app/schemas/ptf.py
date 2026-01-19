from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field

# PTF schemas
class PtfBase(BaseModel):
  name: str
  description: Optional[str] = None
  thumbnail_path: Optional[str] = None
  @computed_field
  @property
  def thumbnail_url(self) -> str:
    """Constructs the full URL path for the frontend"""
    return f"http://localhost:8000/static/{self.thumbnail_path}"

class PtfCreate(PtfBase):
  pass

class PtfRead(PtfBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class PtfReadWithProjets(PtfBase):
  id: int
  projets: Optional[List["PtfRead"]] = []
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class PtfUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None

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