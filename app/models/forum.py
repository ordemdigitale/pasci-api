# app/models/forum.py | Forum models: PoleConcertation, ForumSujet, ForumCommentaire
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, TEXT, func
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
import slugify as slugify_lib

if TYPE_CHECKING:
    from app.models.crasc import Osc


class PoleConcertation(SQLModel, table=True):
    __tablename__ = "pole_concertation"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=150, unique=True)
    slug: Optional[str] = Field(default=None, nullable=True, max_length=150, unique=True)
    category: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    image_path: Optional[str] = Field(default=None, max_length=500)
    objectifs: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))  # JSON list
    objectifs_annuels: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))  # JSON list
    nb_osc_membres: Optional[int] = Field(default=None, nullable=True)
    regions_influence: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))  # JSON list
    realisations: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))  # JSON list
    projets_en_cours: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))  # JSON list
    agenda: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))  # JSON list of {date, titre, description}
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    sujets: List["ForumSujet"] = Relationship(
        back_populates="pole",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    oscs: List["Osc"] = Relationship(
        back_populates="poles",
        sa_relationship_kwargs={"secondary": "osc_pole", "lazy": "selectin"},
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.name and not self.slug:
            self.slug = slugify_lib.slugify(self.name)

    def __repr__(self) -> str:
        return f"<PoleConcertation: {self.name}>"


class ForumSujet(SQLModel, table=True):
    __tablename__ = "forum_sujet"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=255)
    slug: Optional[str] = Field(default=None, nullable=True, max_length=255, unique=True)
    content: str = Field(sa_column=Column(TEXT, nullable=False))
    pole_id: int = Field(foreign_key="pole_concertation.id", ondelete="CASCADE")
    author_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    author_name: Optional[str] = Field(default=None, max_length=200)  # denormalized for display
    is_pinned: bool = Field(default=False)
    views_count: int = Field(default=0)
    comments_count: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    pole: Optional[PoleConcertation] = Relationship(back_populates="sujets")
    commentaires: List["ForumCommentaire"] = Relationship(
        back_populates="sujet",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.title and not self.slug:
            import time
            base = slugify_lib.slugify(self.title)
            self.slug = f"{base}-{int(time.time())}"

    def __repr__(self) -> str:
        return f"<ForumSujet: {self.title}>"


class ForumCommentaire(SQLModel, table=True):
    __tablename__ = "forum_commentaire"

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(sa_column=Column(TEXT, nullable=False))
    sujet_id: int = Field(foreign_key="forum_sujet.id", ondelete="CASCADE")
    author_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    author_name: Optional[str] = Field(default=None, max_length=200)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    sujet: Optional[ForumSujet] = Relationship(back_populates="commentaires")

    def __repr__(self) -> str:
        return f"<ForumCommentaire id={self.id}>"
