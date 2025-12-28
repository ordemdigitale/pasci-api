from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Schemas for OSC Type
class OscTypeBase(BaseModel):
  name: str
  description: Optional[str] = None

class OscTypeCreate(OscTypeBase):
  pass

class OscTypeRead(OscTypeBase):
  id: int
  class Config:
    orm_mode = True

class OscTypeUpdate(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None

# Include related OSCs in the read schema of OscType
class OscTypeReadWithOscs(OscTypeRead):
  oscs: Optional[list["OscRead"]] = []

# Schemas for OSC
class OscBase(BaseModel):
  name: str
  description: Optional[str] = None
  type_id: int
  #region_id: int
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None

class OscCreate(OscBase):
  """ Input schema for creating a new OSC. """
  pass

class OscRead(OscBase):
  id: int
  type: OscTypeRead
  class Config:
    orm_mode = True