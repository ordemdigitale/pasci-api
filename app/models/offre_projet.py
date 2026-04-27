# Model pour représenter les Offres de Projets
## app/models/offre_projet.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, func, TEXT, Integer
from typing import Optional
from uuid import uuid4, UUID
import slugify


class OffreProjet(SQLModel, table=True):
    """
    Represente une Offre de Projet dans la base de données.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    nom: str = Field(max_length=200, nullable=False, description="Nom du projet")
    slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)

    # OSC porteuse
    osc: str = Field(max_length=200, nullable=False, description="OSC porteuse du projet")

    # Informations de base
    domaine: str = Field(max_length=100, nullable=False, description="Domaine d'intervention")
    zone: str = Field(max_length=100, nullable=False, description="Zone géographique")
    durée: str = Field(max_length=50, nullable=False, description="Durée du projet")
    budget: str = Field(max_length=100, nullable=False, description="Budget du projet")

    # Descriptions
    objectif: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Objectif principal du projet")
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Description détaillée")
    beneficiaires: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Bénéficiaires du projet")

    # Statut et progression
    statut: str = Field(default="En attente", max_length=50, description="Statut du projet")
    progression: int = Field(default=0, description="Progression du projet (0-100%)")
    # brouillon | en_attente | publie | rejete
    statut_publication: str = Field(default="publie", max_length=20)

    # Données structurées (JSON)
    resultats_attendus: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Résultats attendus (JSON)")
    partenaires: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Partenaires (JSON)")

    # Image
    image_path: Optional[str] = Field(default="default-project.jpg", nullable=True, max_length=2048, description="Chemin de l'image")

    # Dates
    date_publication: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Date de publication"
    )

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
        if self.nom and not self.slug:
            self.slug = slugify.slugify(self.nom)

    # Representation in admin/logs
    def __repr__(self) -> str:
        return f"<Projet: {self.nom}>"
