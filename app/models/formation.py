# app/models/formation.py
"""
Formation (Training) model for managing training sessions and workshops
"""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func, TEXT
from typing import Optional, List
from uuid import UUID, uuid4
import slugify


class FormationRubrique(SQLModel, table=True):
    """Rubrique/catégorie de formation"""
    __tablename__ = "formation_rubrique"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=150, unique=True, index=True)
    slug: Optional[str] = Field(default=None, max_length=150, unique=True)
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    color: Optional[str] = Field(default="#E05017", max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    formations: List["Formation"] = Relationship(
        back_populates="rubrique",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.name and not self.slug:
            self.slug = slugify.slugify(self.name)

    def __repr__(self) -> str:
        return f"<FormationRubrique: {self.name}>"


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

    # Type et prix
    type: str = Field(default="gratuite", max_length=20)  # "gratuite" ou "payante"
    price: Optional[float] = Field(default=None, description="Prix en FCFA si payante")

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
    rubrique_id: Optional[int] = Field(default=None, foreign_key="formation_rubrique.id", ondelete="SET NULL")
    rubrique: Optional["FormationRubrique"] = Relationship(back_populates="formations")

    crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id", ondelete="SET NULL")
    crasc: Optional["Crasc"] = Relationship(back_populates="formations")

    osc_id: Optional[int] = Field(default=None, foreign_key="osc.id", ondelete="SET NULL")
    osc: Optional["Osc"] = Relationship(back_populates="formations")

    inscriptions: List["FormationInscription"] = Relationship(
        back_populates="formation",
        sa_relationship_kwargs={"passive_deletes": True},
    )

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


class FormationModule(SQLModel, table=True):
    """Module (chapitre) d'une formation"""
    __tablename__ = "formation_module"

    id: Optional[int] = Field(default=None, primary_key=True)
    formation_id: int = Field(foreign_key="formations.id", ondelete="CASCADE")
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    order: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    lecons: List["FormationLecon"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={"passive_deletes": True, "order_by": "FormationLecon.order"},
    )

    def __repr__(self) -> str:
        return f"<FormationModule: {self.title}>"


class FormationLecon(SQLModel, table=True):
    """Leçon au sein d'un module"""
    __tablename__ = "formation_lecon"

    id: Optional[int] = Field(default=None, primary_key=True)
    module_id: int = Field(foreign_key="formation_module.id", ondelete="CASCADE")
    title: str = Field(max_length=200)
    # type: "video" | "pdf" | "text"
    type: str = Field(default="text", max_length=20)
    # Pour video : URL YouTube/Vimeo
    # Pour pdf uploadé : chemin fichier
    # Pour text : contenu HTML/markdown
    content: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    file_path: Optional[str] = Field(default=None, max_length=500)
    duration_minutes: Optional[int] = Field(default=None)
    is_preview: bool = Field(default=False)  # visible sans inscription
    order: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    module: Optional["FormationModule"] = Relationship(back_populates="lecons")

    def __repr__(self) -> str:
        return f"<FormationLecon: {self.title} ({self.type})>"


class FormationInscription(SQLModel, table=True):
    """Inscription d'un participant à une formation"""
    __tablename__ = "formation_inscription"

    id: Optional[int] = Field(default=None, primary_key=True)
    formation_id: int = Field(foreign_key="formations.id", ondelete="CASCADE")
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    participant_name: str = Field(max_length=200)
    participant_email: str = Field(max_length=255)
    is_completed: bool = Field(default=False)
    completed_at: Optional[datetime] = Field(default=None)
    certificate_issued: bool = Field(default=False)

    # ── Paiement CinetPay ──────────────────────────────────────
    # payment_status : "gratuite" | "pending" | "paid" | "failed"
    payment_status: str = Field(default="gratuite", max_length=20)
    payment_transaction_id: Optional[str] = Field(default=None, max_length=100, unique=True)
    payment_notify_token: Optional[str] = Field(default=None, max_length=500)  # notify_token CinetPay v1
    payment_amount: Optional[float] = Field(default=None)
    payment_date: Optional[datetime] = Field(default=None)
    payment_operator: Optional[str] = Field(default=None, max_length=100)  # ex: "ORANGE_CI"

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    formation: Optional["Formation"] = Relationship(back_populates="inscriptions")
    certificat: Optional["Certificat"] = Relationship(
        back_populates="inscription",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    def __repr__(self) -> str:
        return f"<Inscription: {self.participant_name} → {self.formation_id}>"


class Certificat(SQLModel, table=True):
    """Certificat numérique délivré après complétion d'une formation"""
    __tablename__ = "certificat"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        default_factory=lambda: str(uuid4()).replace("-", "").upper()[:16],
        max_length=20,
        unique=True,
        index=True,
    )
    inscription_id: int = Field(foreign_key="formation_inscription.id", ondelete="CASCADE")
    formation_title: str = Field(max_length=250)
    participant_name: str = Field(max_length=200)
    participant_email: str = Field(max_length=255)
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    inscription: Optional["FormationInscription"] = Relationship(back_populates="certificat")

    def __repr__(self) -> str:
        return f"<Certificat: {self.code} — {self.participant_name}>"


class FormationAvis(SQLModel, table=True):
    """Avis d'un participant sur une formation"""
    __tablename__ = "formation_avis"

    id: Optional[int] = Field(default=None, primary_key=True)
    formation_id: int = Field(foreign_key="formations.id", ondelete="CASCADE", index=True)
    inscription_id: int = Field(foreign_key="formation_inscription.id", ondelete="CASCADE", unique=True)
    participant_name: str = Field(max_length=200)
    note: int = Field(ge=1, le=5)
    commentaire: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class FormationProgression(SQLModel, table=True):
    """Suivi de progression : leçons vues par inscription"""
    __tablename__ = "formation_progression"

    id: Optional[int] = Field(default=None, primary_key=True)
    inscription_id: int = Field(foreign_key="formation_inscription.id", ondelete="CASCADE", index=True)
    lecon_id: int = Field(foreign_key="formation_lecon.id", ondelete="CASCADE", index=True)
    viewed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
