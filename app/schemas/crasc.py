from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field

######################
# Schemas for RegionCiv
######################
class RegionCivBase(BaseModel):
  name: str
  crasc_id: Optional[int] = Field(default=None, foreign_key="crascregion.id")

class RegionCivCreate(RegionCivBase):
  pass

class RegionCivRead(RegionCivBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class RegionCivReadWithCrascRegion(RegionCivBase):
  id: int
  slug: Optional[str] = None
  crasc_region: Optional["CrascRegionRead"]
  class Config:
    from_attributes = True

class RegionCivUpdate(BaseModel):
  name: Optional[str] = None
  crasc_id: Optional[int] = None

######################
# Schemas for CRASC Region
######################
class CrascRegionBase(BaseModel):
  name: str
  description: Optional[str] = None
  osc_count: Optional[int] = 0

class CrascRegionCreate(CrascRegionBase):
  order: Optional[int] = None

class CrascRegionRead(CrascRegionBase):
  id: int
  slug: Optional[str] = None
  order: Optional[int] = None
  class Config:
    from_attributes = True

class CrascRegionReadWithOscs(CrascRegionBase):
  id: int
  oscs: Optional[List["OscRead"]] = []
  class Config:
    from_attributes = True

class CrascRegionUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  order: Optional[int] = None
  osc_count: Optional[int] = None

# Crasc region with oscs and region civs
class CrascRegionReadWithOscsAndRegionCivs(CrascRegionBase):
  id: int
  oscs: Optional[List["OscRead"]] = []
  regions_civ: Optional[List[RegionCivRead]] = []
  class Config:
    from_attributes = True

######################
# Schemas for OSC Type
######################
class OscTypeBase(BaseModel):
  name: str
  description: Optional[str] = None

class OscTypeCreate(OscTypeBase):
  pass

class OscTypeRead(OscTypeBase):
  id: int
  class Config:
    from_attributes = True

class OscTypeReadWithOscs(OscTypeBase):
  id: int
  oscs: Optional[list["OscRead"]] = []
  class Config:
    from_attributes = True

class OscTypeUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None

#################
# Schemas for OSC
#################
class OscBase(BaseModel):
  name: str
  description: Optional[str] = None
  thumbnail_path: Optional[str] = None
  type_id: int
  region_id: int
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None
  @computed_field
  @property
  def thumbnail_url(self) -> str:
    """Constructs the full URL path for the frontend"""
    return f"http://localhost:8000/static/{self.thumbnail_path}"

class OscCreate(OscBase):
  """ Input schema for creating a new OSC. """
  pass

class OscRead(OscBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class OscReadWithOscType(OscBase):
  id: int
  type: OscTypeRead
  class Config:
    from_attributes = True

class OscReadWithCrascRegion(OscBase):
  id: int
  region: CrascRegionRead
  class Config:
    from_attributes = True

class OscReadWithCrascRegionAndOscType(OscBase):
  id: int
  type: OscTypeRead
  region: CrascRegionRead
  class Config:
    from_attributes = True

#################
# Schemas for News
#################
class NewsBase(BaseModel):
  title: str
  slug: Optional[str] = None
  content: Optional[str] = None
  thumbnail_path: Optional[str] = None
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
  class Config:
    from_attributes = True

class NewsReadWithCrascAndOsc(NewsBase):
  id: int
  crasc: Optional[CrascRegionRead] = None
  osc: Optional[OscRead] = None
  class Config:
    from_attributes = True

class NewsUpdate(BaseModel):
  title: Optional[str] = None
  content: Optional[str] = None
  osc_id: Optional[int] = None
  crasc_id: Optional[int] = None