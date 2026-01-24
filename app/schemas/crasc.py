from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field


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
  region_id: Optional[int] = Field(default=None, foreign_key="region.id") 
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None
  @computed_field
  @property
  def thumbnail_url(self) -> str:
    """Constructs the full URL path for the frontend"""
    return f"http://localhost:8000/static/{self.thumbnail_path}"

class OscCreate(OscBase):
  pass

class OscRead(OscBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class OscReadDetail(OscBase):
  id: int
  slug: Optional[str] = None
  type: Optional[OscTypeRead] = None
  crasc: Optional[CrascRead] = None
  news_items: Optional[List["NewsRead"]] = []
  class Config:
    from_attributes = True
    
class OscUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  type_id: Optional[int] = None
  crasc_id: Optional[int] = None
  address: Optional[str] = None


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
    return f"http://localhost:8000/static/{self.thumbnail_path}"

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