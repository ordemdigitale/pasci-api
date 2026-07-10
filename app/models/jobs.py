# models/jobs.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, func, TEXT
from typing import Optional
from uuid import uuid4, UUID
import slugify

class Jobs(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(max_length=200, nullable=False, description="Job title")
    employer: str = Field(max_length=200, nullable=False)
    description: str = Field(sa_column=Column(String, nullable=True), description="Job description")
    location: str = Field(max_length=100, nullable=False, description="Job location")
    type: str = Field(max_length=200, nullable=False, description="Job type")
    offre_url: Optional[str] = Field(default=None, nullable=True, max_length=500, description="Lien pour plus d'informations ou candidature")
    is_expired: bool = Field(default=False, description="Indicates if the job posting is expired")
    slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
    # brouillon | en_attente | publie | rejete
    statut_publication: str = Field(default="publie", max_length=20)

    # Nouveaux champs pour le détail de l'offre (stockés en JSON)
    missions: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Missions et responsabilités (JSON)")
    requirements: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Exigences du profil recherché (JSON)")
    benefits: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Avantages et culture (JSON)")
    # Publication date that defaults to now if not provided
    publication_date: Optional[datetime] = Field(
       default_factory=lambda: datetime.now(timezone.utc),
       sa_column=Column(DateTime(timezone=True), server_default=func.now()),
       description="Date when the job was published")
    expiration_date: Optional[datetime] = Field(
       default_factory=lambda: datetime.now(timezone.utc),
       sa_column=Column(DateTime(timezone=True), server_default=func.now()),
       description="Date when the job expires")
    # Timestamps (auto-managed)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc),
      sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    # Création automatique de slug
    def __init__(self, **kwargs):
      super().__init__(**kwargs)
      if self.title and not self.slug:
        self.slug = slugify.slugify(self.title)

    # Representation in admin/logs
    def __repr__(self) -> str:
      return f"<Poste: {self.title}>"
