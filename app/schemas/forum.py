# app/schemas/forum.py | Schemas for forum feature
from datetime import datetime
from typing import Literal, Optional, List
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
    projets_en_cours: Optional[str] = None  # JSON string
    agenda: Optional[str] = None  # JSON string
    is_active: bool = True


class PoleConcertationCreate(PoleConcertationBase):
    pass


class PoleConcertationRead(PoleConcertationBase):
    id: int
    slug: str
    created_at: datetime
    sujets_count: Optional[int] = 0
    nb_membres_actifs: Optional[int] = 0

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
    projets_en_cours: Optional[str] = None
    agenda: Optional[str] = None
    is_active: Optional[bool] = None


# ──────────────── Sondages / Votes ────────────────

SondageStatus = Literal["ouvert", "ferme"]
SondageResultsVisibility = Literal["always", "after_vote", "after_close"]


class PoleSondageCreate(BaseModel):
    question: str
    description: Optional[str] = None
    options: List[str]
    status: SondageStatus = "ouvert"
    results_visibility: SondageResultsVisibility = "after_vote"
    closes_at: Optional[datetime] = None


class PoleSondageUpdate(BaseModel):
    question: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SondageStatus] = None
    results_visibility: Optional[SondageResultsVisibility] = None
    closes_at: Optional[datetime] = None


class PoleSondageOptionRead(BaseModel):
    id: int
    label: str
    ordre: int
    votes_count: int = 0
    percentage: float = 0


class PoleSondageRead(BaseModel):
    id: int
    pole_id: int
    question: str
    description: Optional[str] = None
    status: str
    results_visibility: str
    closes_at: Optional[datetime] = None
    created_at: datetime
    total_votes: int = 0
    user_vote_option_id: Optional[int] = None
    can_show_results: bool = False
    options: List[PoleSondageOptionRead] = []

    class Config:
        from_attributes = True


class PoleSondageVoteCreate(BaseModel):
    option_id: int


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
