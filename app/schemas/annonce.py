# schemas/annonce.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnnonceBase(BaseModel):
    texte: str
    is_active: bool = True
    ordre: int = 0
    date_fin: Optional[datetime] = None


class AnnonceCreate(AnnonceBase):
    pass


class AnnonceRead(AnnonceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnnonceUpdate(BaseModel):
    texte: Optional[str] = None
    is_active: Optional[bool] = None
    ordre: Optional[int] = None
    date_fin: Optional[datetime] = None
