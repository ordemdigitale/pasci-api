from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Schemas for CRASC Region
class CrascRegionBase(BaseModel):
  name: str
  description: Optional[str] = None

class CrascRegionCreate(CrascRegionBase):
  pass

class CrascRegionRead(CrascRegionBase):
  id: int
  class Config:
    from_attributes = True

class CrascRegionReadWithOscs(CrascRegionBase):
  id: int
  oscs: Optional[List["OscRead"]] = []
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
  type_id: int
  region_id: int
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None

class OscCreate(OscBase):
  """ Input schema for creating a new OSC. """
  pass

class OscRead(OscBase):
  id: int
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