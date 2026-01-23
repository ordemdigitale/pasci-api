# app/models/formation.py
"""
Formation (Training) model for managing training sessions and workshops
"""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func, TEXT
from typing import Optional, List
import slugify


class Formation(SQLModel, table=True):
    """
    Training/Workshop model for educational sessions
    """
    __tablename__ = "formations"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, unique=True, index=True, description="Titre de la formation")
    slug: Optional[str] = Field(default=None, max_length=250, unique=True, index=True)
    description: Optional[str] = Field(sa_column=Column(TEXT, nullable=True), description="Description détaillée")

    # Training details
    trainer: Optional[str] = Field(None, max_length=200, description="Nom du formateur")
    location: Optional[str] = Field(None, max_length=200, description="Lieu de la formation")

    # Dates
    start_date: Optional[datetime] = Field(None, description="Date de début")
    end_date: Optional[datetime] = Field(None, description="Date de fin")
    registration_deadline: Optional[datetime] = Field(None, description="Date limite d'inscription")

    # Capacity
    max_participants: Optional[int] = Field(None, ge=1, description="Nombre maximum de participants")
    current_participants: int = Field(default=0, ge=0, description="Nombre actuel de participants")

    # Status
    is_published: bool = Field(default=False, description="Formation publiée et visible")
    is_full: bool = Field(default=False, description="Formation complète")
    is_completed: bool = Field(default=False, description="Formation terminée")

    # Media
    thumbnail_path: Optional[str] = Field(default="default.png", max_length=2048)

    # Links and resources
    registration_link: Optional[str] = Field(None, max_length=500, description="Lien d'inscription")
    materials_link: Optional[str] = Field(None, max_length=500, description="Lien vers les supports de formation")

    # Relations
    crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id", ondelete="SET NULL")
    crasc: Optional["Crasc"] = Relationship(back_populates="formations")

    osc_id: Optional[int] = Field(default=None, foreign_key="osc.id", ondelete="SET NULL")
    osc: Optional["Osc"] = Relationship(back_populates="formations")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.title and not self.slug:
            self.slug = slugify.slugify(self.title)
        # Auto-set is_full based on capacity
        if self.max_participants and self.current_participants >= self.max_participants:
            self.is_full = True

    def __repr__(self) -> str:
        return f"<Formation: {self.title}>"
