# app/schemas/forum.py | Schemas for forum feature
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
import json


# ──────────────── Pôle de concertation ────────────────

class PoleConcertationBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None
    objectifs: Optional[str] = None  # JSON string
    objectifs_annuels: Optional[str] = None  # JSON string
    nb_osc_membres: Optional[int] = None
    regions_influence: Optional[str] = None  # JSON string
    realisations: Optional[str] = None  # JSON string
    agenda: Optional[str] = None  # JSON string
    is_active: bool = True


class PoleConcertationCreate(PoleConcertationBase):
    pass


class PoleConcertationRead(PoleConcertationBase):
    id: int
    slug: str
    created_at: datetime
    sujets_count: Optional[int] = 0

    @property
    def objectifs_list(self) -> List[str]:
        if self.objectifs:
            try:
                return json.loads(self.objectifs)
            except Exception:
                return []
        return []

    class Config:
        from_attributes = True


class PoleConcertationUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None
    objectifs: Optional[str] = None
    objectifs_annuels: Optional[str] = None
    nb_osc_membres: Optional[int] = None
    regions_influence: Optional[str] = None
    realisations: Optional[str] = None
    agenda: Optional[str] = None
    is_active: Optional[bool] = None


# ──────────────── Forum Sujet ────────────────

class ForumSujetCreate(BaseModel):
    title: str
    content: str


class ForumSujetRead(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    pole_id: int
    author_id: Optional[UUID] = None
    author_name: Optional[str] = None
    is_pinned: bool
    views_count: int
    comments_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ForumSujetUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None


# ──────────────── Forum Commentaire ────────────────

class ForumCommentaireCreate(BaseModel):
    content: str


class ForumCommentaireRead(BaseModel):
    id: int
    content: str
    sujet_id: int
    author_id: Optional[UUID] = None
    author_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ForumCommentaireUpdate(BaseModel):
    content: str


# ──────────────── Sujet detail (with comments) ────────────────

class ForumSujetDetail(ForumSujetRead):
    commentaires: List[ForumCommentaireRead] = []
