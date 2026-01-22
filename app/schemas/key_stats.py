# schemas/key_stats.py
from pydantic import BaseModel
from typing import Optional, List


class KeyStatsBase(BaseModel):
  name: str
  number: Optional[int] = None

class KeyStatsCreate(KeyStatsBase):
  pass

class KeyStatsRead(KeyStatsBase):
  id: int
  class Config:
    from_attributes = True

class KeyStatsUpdate(BaseModel):
  name: Optional[str] = None
  number: Optional[int] = None