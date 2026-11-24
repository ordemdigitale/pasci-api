# app/schemas/forum.py | Schemas for forum feature
from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, computed_field
from uuid import UUID
import json

from app.core.config import settings


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
    # [{"nom": "Gbêkê", "nb": 45}, ...] de la région la plus représentée à la moins représentée
    regions_effectifs: List[dict] = []
    # [{"id": "...", "nom": "..."}] : experts qui animent le pôle
    experts: List[dict] = []

    @computed_field
    @property
    def image_url(self) -> Optional[str]:
        if not self.image_path:
            return None
        if self.image_path.startswith("http") or self.image_path.startswith("/"):
            return self.image_path
        return f"{settings.API_BASE_URL}/static/{self.image_path}"

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


class PoleMembreRead(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    sigle: Optional[str] = None
    type_id: Optional[int] = None
    type_name: Optional[str] = None
    categorie: Optional[str] = None
    region_nom: Optional[str] = None
    ville: Optional[str] = None
    thumbnail_url: Optional[str] = None
    crasc_id: Optional[int] = None
    crasc_nom: Optional[str] = None
    axe: Optional[str] = None
    specialites: Optional[str] = None
    # Membre actif : l'OSC a déjà lancé au moins un sujet de discussion dans le pôle
    est_actif: bool = False


class PoleFusionRequest(BaseModel):
    cible_slug: str
    # Nouveau nom du pôle fusionné (ex. "Gouvernance, société civile, paix et sécurité")
    nouveau_nom: Optional[str] = None


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
    est_clos: bool = False
    synthese: Optional[str] = None
    synthese_par: Optional[str] = None
    synthese_le: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ForumSujetUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None


# ──────────────── Pièces jointes (photo, audio, vidéo) ────────────────

class PieceJointeRead(BaseModel):
    id: int
    type: Literal["image", "audio", "video"]
    url: str
    nom: Optional[str] = None
    mime: Optional[str] = None
    taille: int = 0


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
    pieces_jointes: List["PieceJointeRead"] = []

    class Config:
        from_attributes = True


class ForumCommentaireUpdate(BaseModel):
    content: str


# ──────────────── Sujet detail (with comments) ────────────────

class ForumSujetDetail(ForumSujetRead):
    commentaires: List[ForumCommentaireRead] = []
    pieces_jointes: List["PieceJointeRead"] = []
    experts: List[dict] = []


# ──────────────── Synthèse d'une discussion ────────────────

class SyntheseUpdate(BaseModel):
    synthese: Optional[str] = None
    est_clos: Optional[bool] = None


class ContributionRead(BaseModel):
    id: int
    auteur: str
    osc: Optional[str] = None
    date: datetime
    contenu: str
    pieces_jointes: List[PieceJointeRead] = []


class ContributionsSujetRead(BaseModel):
    """Toutes les idées d'une discussion, rassemblées pour la synthèse."""
    sujet: ForumSujetRead
    pole_nom: str
    pole_slug: str
    contributions: List[ContributionRead]
    nb_contributions: int
    nb_participants: int
    nb_osc: int
    mots_cles: List[str]
    brouillon: str


# ─────────────────────────────────────────────────────
# TASK FORCES (groupes d'OSC de l'espace collaboratif)
# ─────────────────────────────────────────────────────

class TaskForceOscMembre(BaseModel):
    """OSC membre d'une task force."""

    id: int
    name: str
    slug: Optional[str] = None
    sigle: Optional[str] = None
    region_nom: Optional[str] = None
    email: Optional[str] = None
    chef_de_file: bool = False

    class Config:
        from_attributes = True


class TaskForceOscBase(BaseModel):
    nom: str = Field(min_length=1, max_length=200)
    thematique: Optional[str] = Field(default=None, max_length=200)
    # Nord, Sud, Est, Ouest, Centre (vide hors découpage régional)
    zone: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    pole_id: Optional[int] = None
    ordre: int = 0
    actif: bool = True


class TaskForceOscCreate(TaskForceOscBase):
    # OSC membres, par identifiant d'annuaire
    osc_ids: List[int] = []
    chef_de_file_id: Optional[int] = None


class TaskForceOscUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=200)
    thematique: Optional[str] = Field(default=None, max_length=200)
    zone: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    pole_id: Optional[int] = None
    ordre: Optional[int] = None
    actif: Optional[bool] = None
    osc_ids: Optional[List[int]] = None
    chef_de_file_id: Optional[int] = None


class TaskForceOscRead(TaskForceOscBase):
    id: int
    slug: Optional[str] = None
    pole_nom: Optional[str] = None
    nb_membres: int = 0
    # Personnes siégeant dans la task force (lucarne « Membres »)
    nb_personnes: int = 0
    nb_documents: int = 0
    membres: List[TaskForceOscMembre] = []
    created_at: datetime

    class Config:
        from_attributes = True


class TaskForceMembreBase(BaseModel):
    """Personne siégeant dans une task force au nom d'une OSC."""

    osc_id: Optional[int] = None
    titre: Optional[str] = Field(default=None, max_length=100)
    nom: str = Field(min_length=1, max_length=200)
    fonction: Optional[str] = Field(default=None, max_length=200)
    contact: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    zone_crasc: Optional[str] = Field(default=None, max_length=100)
    # Groupes thématiques, séparés par des virgules
    groupes_thematiques: Optional[str] = Field(default=None, max_length=500)
    role: Optional[str] = Field(default=None, max_length=100)
    est_coordonnateur: bool = False
    ordre: int = 0


class TaskForceMembreCreate(TaskForceMembreBase):
    pass


class TaskForceMembreUpdate(BaseModel):
    osc_id: Optional[int] = None
    titre: Optional[str] = None
    nom: Optional[str] = Field(default=None, min_length=1, max_length=200)
    fonction: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    zone_crasc: Optional[str] = None
    groupes_thematiques: Optional[str] = None
    role: Optional[str] = None
    est_coordonnateur: Optional[bool] = None
    ordre: Optional[int] = None


class TaskForceMembreRead(TaskForceMembreBase):
    id: int
    task_force_id: int
    osc_nom: Optional[str] = None
    osc_slug: Optional[str] = None
    # Renseigné pour la task force nationale : d'où vient le coordonnateur
    task_force_nom: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskForceDocumentRead(BaseModel):
    id: int
    task_force_id: Optional[int] = None
    task_force_nom: Optional[str] = None
    categorie: str
    sous_categorie: Optional[str] = None
    titre: str
    description: Optional[str] = None
    fichier_url: Optional[str] = None
    fichier_nom: Optional[str] = None
    taille_octets: Optional[int] = None
    auteur_nom: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ArborescenceCategorie(BaseModel):
    categorie: str
    sous_categories: List[str] = []
    nb_documents: int = 0
