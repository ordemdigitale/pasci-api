from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field

# Team schemas
class TeamBase(BaseModel):
  name: str

class TeamCreate(TeamBase):
  pass

class TeamRead(TeamBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class TeamReadWithHeroes(TeamBase):
  id: int
  heroes: Optional[List["HeroRead"]] = []
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class TeamUpdate(BaseModel):
  name: Optional[str] = None

# Hero schemas
class HeroBase(BaseModel):
  name: str
  team_id: Optional[int] = Field(default=None, foreign_key="team.id")

class HeroCreate(HeroBase):
  team: Optional[TeamRead] = None

class HeroRead(HeroBase):
  id: int
  slug: Optional[str] = None
  class Config:
    from_attributes = True

class HeroReadWithTeam(HeroBase):
  id: int
  team: Optional[TeamRead] = None

class HeroUpdate(BaseModel):
  name: Optional[str] = None
  team_id: Optional[int] = None