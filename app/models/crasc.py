# models/crasc.py (Model name CRASC + related models)
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func, TEXT, ForeignKey, Integer, Table, UniqueConstraint
from sqlalchemy.event import listens_for
from typing import Optional, List
import slugify, re
from app.models.tags import NewsTag
from sqlmodel import SQLModel as _SM


# ─── Table de liaison OSC ↔ Pôle de concertation (many-to-many) ───
osc_pole_link = Table(
    "osc_pole",
    _SM.metadata,
    Column("osc_id", Integer, ForeignKey("osc.id", ondelete="CASCADE"), primary_key=True),
    Column("pole_id", Integer, ForeignKey("pole_concertation.id", ondelete="CASCADE"), primary_key=True),
)


class Crasc(SQLModel, table=True):
  """ Represente un CRASC dans la base de données. """
  name: str = Field(nullable=False, max_length=100, unique=True, description="Nom du CRASC.")
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
  description: Optional[str] = Field(default=None, nullable=True, max_length=100)
  osc_count: Optional[int] = Field(default=0, nullable=True, description="Nombre d'OSCs membre du CRASC")
  email_pca: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Email du PCA du CRASC")

  regions: List["Region"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  oscs: List["Osc"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  news_items: List["News"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  formations: List["Formation"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  documents: List["Documentation"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  evenements: List["Evenement"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  videos: List["CrascVideo"] = Relationship(
    back_populates="crasc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  id: Optional[int] = Field(default=None, primary_key=True)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )

  # Création automatique de slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)

  # Representation dans admin/logs
  def __repr__(self) -> str:
    return f"<Nom du CRASC: {self.name}>"


class Region(SQLModel, table=True):
  """
    Représente une région administrative de la Côte d'Ivoire dans la base de données.
  """
  name: str = Field(nullable=False, max_length=100, unique=True, description="Nom de la région")
  crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id", ondelete="SET NULL")
  crasc: Optional[Crasc] = Relationship(back_populates="regions")
  id: Optional[int] = Field(default=None, primary_key=True)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )  

  # Création automatique de slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)

  # Representation dans admin/logs
  def __repr__(self) -> str:
    return f"<Région de la Côte d'Ivoire: {self.name}>"


class OscType(SQLModel, table=True):
  """ Represente un type de OSC dans la base de données. """
  name: str = Field(index=True, unique=True)
  description: Optional[str] = None
  oscs: List["Osc"] = Relationship(
    back_populates="type",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  id: Optional[int] = Field(default=None, primary_key=True)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )

  # Création automatique de slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)
  
  # Representation dans admin/logs
  def __repr__(self) -> str:
    return f"<Type de OSC: {self.name}>"
  

class Osc(SQLModel, table=True):
  """
    Represente une OSC (Organisation de la Société Civile) dans la base de données.
  """
  name: str = Field(index=True, unique=True)
  sigle: Optional[str] = Field(default=None, nullable=True, max_length=100, description="Sigle ou abréviation")
  description: Optional[str] = Field(default=None, nullable=True, max_length=500)
  thumbnail_path: Optional[str] = Field(default="default.png", nullable=True, max_length=2048)

  type_id: Optional[int] = Field(default=None, foreign_key="osctype.id", ondelete="SET NULL")
  type: Optional[OscType] = Relationship(back_populates="oscs")

  crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id", ondelete="SET NULL")
  crasc: Optional[Crasc] = Relationship(back_populates="oscs")

  region_id: Optional[int] = Field(default=None, foreign_key="region.id", ondelete="SET NULL")
  region: Optional["Region"] = Relationship()

  # Coordonnées géographiques
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None

  # Informations de contact pour l'annuaire
  email: Optional[str] = Field(default=None, nullable=True, max_length=255, description="Email de contact")
  phone: Optional[str] = Field(default=None, nullable=True, max_length=50, description="Numéro de téléphone")
  region_nom: Optional[str] = Field(default=None, nullable=True, max_length=150, description="Région déclarée")
  departement: Optional[str] = Field(default=None, nullable=True, max_length=150, description="Département")
  sous_prefecture: Optional[str] = Field(default=None, nullable=True, max_length=150, description="Sous-préfecture")
  ville: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Ville de l'OSC")
  origine_organisation: Optional[str] = Field(default=None, nullable=True, max_length=50, description="Lieu de naissance de l'organisation")

  # Informations complémentaires
  website: Optional[str] = Field(default=None, nullable=True, max_length=500, description="Site web")
  reseaux_sociaux: Optional[str] = Field(default=None, nullable=True, description="Réseaux sociaux")
  date_creation: Optional[str] = Field(default=None, nullable=True, max_length=30, description="Date de création")
  numero_recepisse: Optional[str] = Field(default=None, nullable=True, max_length=200, description="N° récépissé")
  type_document_formalisation: Optional[str] = Field(
    default=None,
    nullable=True,
    max_length=50,
    description="Niveau/type de document de formalisation de l'OSC",
  )
  document_formalisation_path: Optional[str] = Field(
    default=None,
    nullable=True,
    max_length=2048,
    description="Chemin du justificatif de formalisation de l'OSC",
  )
  existence_siege: Optional[bool] = Field(default=None, nullable=True, description="L'OSC dispose d'un siège")
  manuel_procedures: Optional[bool] = Field(default=None, nullable=True, description="L'OSC dispose d'un manuel de procédures")
  plan_action: Optional[bool] = Field(default=None, nullable=True, description="L'OSC dispose d'un plan d'action")
  plan_action_document_path: Optional[str] = Field(default=None, nullable=True, max_length=2048, description="Chemin de la preuve du plan d'action")
  rapports_annuels: Optional[bool] = Field(default=None, nullable=True, description="L'OSC rédige des rapports annuels d'activités")
  rapports_annuels_document_path: Optional[str] = Field(default=None, nullable=True, max_length=2048, description="Chemin de la preuve des rapports annuels")
  niveau_couverture: Optional[str] = Field(default=None, nullable=True, max_length=100, description="Niveau de couverture")
  zone_couverture: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Zone de couverture")
  categorie: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Catégorie d'organisation")
  domaine_prioritaire: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Domaine d'activité prioritaire")
  domaine_prioritaire_2: Optional[str] = Field(default=None, nullable=True, max_length=200, description="2ème domaine prioritaire")
  domaine_prioritaire_3: Optional[str] = Field(default=None, nullable=True, max_length=200, description="3ème domaine prioritaire")
  domaine_prioritaire_4: Optional[str] = Field(default=None, nullable=True, max_length=200, description="4ème domaine prioritaire")
  domaine_prioritaire_5: Optional[str] = Field(default=None, nullable=True, max_length=200, description="5ème domaine prioritaire")
  nb_membres: Optional[int] = Field(default=None, nullable=True, description="Nombre de membres")
  nb_femmes_membres: Optional[int] = Field(default=None, nullable=True, description="Nombre de femmes membres")
  nb_hommes_membres: Optional[int] = Field(default=None, nullable=True, description="Nombre d'hommes membres")
  nb_membres_jeunes: Optional[int] = Field(default=None, nullable=True, description="Nombre de membres jeunes")
  nb_membres_handicap: Optional[int] = Field(default=None, nullable=True, description="Nombre de membres en situation de handicap")
  nb_membres_be: Optional[int] = Field(default=None, nullable=True, description="Nombre de membres du bureau exécutif")
  nombre_mandats_be: Optional[int] = Field(default=None, nullable=True, description="Nombre de mandats du BE ou DE actuel")
  nb_personnes_engagees: Optional[int] = Field(default=None, nullable=True, description="Nombre de personnes engagées")
  nb_cdi: Optional[int] = Field(default=None, nullable=True, description="Nombre de CDI")
  nb_cdd: Optional[int] = Field(default=None, nullable=True, description="Nombre de CDD")
  nb_beneficiaires: Optional[int] = Field(default=None, nullable=True, description="Nombre de bénéficiaires")
  nb_femmes_beneficiaires: Optional[int] = Field(default=None, nullable=True, description="Nombre de femmes bénéficiaires")
  nb_jeunes_beneficiaires: Optional[int] = Field(default=None, nullable=True, description="Nombre de jeunes bénéficiaires")
  nb_beneficiaires_handicap: Optional[int] = Field(default=None, nullable=True, description="Nombre de bénéficiaires en situation de handicap")
  nb_activites: Optional[int] = Field(default=None, nullable=True, description="Nombre d'activités réalisées")
  date_derniere_activite: Optional[str] = Field(default=None, nullable=True, max_length=30, description="Date de la dernière activité réalisée")
  budget_annuel: Optional[int] = Field(default=None, nullable=True, description="Budget annuel en F/CFA")
  type_financement: Optional[str] = Field(default=None, nullable=True, max_length=500, description="Types de financement")
  etat_cotisations: Optional[str] = Field(default=None, nullable=True, max_length=200, description="État des cotisations")
  montant_cotisation: Optional[int] = Field(default=None, nullable=True, description="Montant de la cotisation")
  nom_president: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Nom du président")
  sexe_president: Optional[str] = Field(default=None, nullable=True, max_length=20, description="Sexe du président")
  mode_designation_president: Optional[str] = Field(default=None, nullable=True, max_length=200, description="Mode de désignation du président")
  date_designation_responsable: Optional[str] = Field(default=None, nullable=True, max_length=30, description="Date de désignation du/de la responsable actuel(le)")
  date_prochaine_designation: Optional[str] = Field(default=None, nullable=True, max_length=30, description="Prochaine date de désignation")
  duree_mandat_be: Optional[str] = Field(default=None, nullable=True, max_length=100, description="Durée du mandat du bureau exécutif")
  adhesion_crasc: Optional[bool] = Field(default=None, nullable=True, description="Adhésion au CRASC")
  adhesion_crasc_statut: Optional[str] = Field(default=None, nullable=True, max_length=20, description="Statut d'adhésion au CRASC")
  adhesion_crasc_document_path: Optional[str] = Field(default=None, nullable=True, max_length=2048, description="Chemin de la preuve d'adhésion au CRASC")
  niveau_regroupement: Optional[str] = Field(
    default=None,
    nullable=True,
    max_length=30,
    description="Niveau de regroupement de l'OSC",
  )
  reseau_appartenance: Optional[str] = Field(default=None, nullable=True, description="Réseau d'appartenance")
  organes_gouvernance: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Organes de gouvernance")
  pays_couverture: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Pays de couverture")
  secteurs_activites: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Secteurs d'activités")
  populations_cibles: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Populations cibles")
  savoir_faire: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Savoir-faire / expertise")
  plan_action_annee_cours: Optional[bool] = Field(default=None, nullable=True, description="Plan d'action pour l'année en cours")
  plan_action_annee_cours_details: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Plan d'action et activités à venir")
  difficultes: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Difficultés rencontrées")
  recommandations: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Recommandations")
  recommandations_2: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True), description="Deuxième recommandation")
  # Sources de financement (booléens)
  financement_cotisation: Optional[bool] = Field(default=None, nullable=True)
  financement_dons: Optional[bool] = Field(default=None, nullable=True)
  financement_legs: Optional[bool] = Field(default=None, nullable=True)
  financement_collectivites: Optional[bool] = Field(default=None, nullable=True)
  financement_fonds_propres: Optional[bool] = Field(default=None, nullable=True)
  financement_ong_intl: Optional[bool] = Field(default=None, nullable=True)
  financement_multilateral: Optional[bool] = Field(default=None, nullable=True)
  is_visible: bool = Field(default=True, description="Afficher l'OSC dans l'annuaire public")

  news_items: List["News"] = Relationship(
    back_populates="osc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  formations: List["Formation"] = Relationship(
    back_populates="osc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  documents: List["Documentation"] = Relationship(
    back_populates="osc",
    sa_relationship_kwargs={"passive_deletes": True}
  )
  poles: List["PoleConcertation"] = Relationship(
    back_populates="oscs",
    sa_relationship_kwargs={"secondary": "osc_pole", "lazy": "selectin"},
  )
  id: Optional[int] = Field(default=None, primary_key=True)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )

  # Création automatique de slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)

  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Nome de l'OSC: {self.name}>"


class News(SQLModel, table=True):
  title: str = Field(index=True, unique=True, description="Titre de l'actualité.")
  content: Optional[str] = Field(sa_column=Column(TEXT, nullable=True), description="Corps de l'article.")
  thumbnail_path: Optional[str] = Field(default="default.png", nullable=True, max_length=2048)
  
  osc_id: Optional[int] = Field(default=None, nullable=True, foreign_key="osc.id", ondelete="SET NULL")
  osc: Optional[Osc] = Relationship(back_populates="news_items")
  
  crasc_id: Optional[int] = Field(default=None, nullable=True, foreign_key="crasc.id", ondelete="SET NULL")
  crasc: Optional[Crasc] = Relationship(back_populates="news_items")

  # Many-to-Many relationship with Tags
  tags: List["Tag"] = Relationship(back_populates="news_items", link_model=NewsTag)

  id: Optional[int] = Field(default=None, primary_key=True)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
  # brouillon | en_attente | publie | rejete
  statut_publication: str = Field(default="publie", max_length=20)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
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
    return f"<Titre: {self.title}>"


class CrascVideo(SQLModel, table=True):
  """Représente une vidéo (YouTube/Vimeo) associée à un CRASC."""
  __tablename__ = "crasc_video"

  id: Optional[int] = Field(default=None, primary_key=True)
  crasc_id: int = Field(foreign_key="crasc.id", ondelete="CASCADE", nullable=False)
  crasc: Optional[Crasc] = Relationship(back_populates="videos")
  titre: str = Field(max_length=200, nullable=False)
  url: str = Field(max_length=500, nullable=False)
  description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
  ordre: int = Field(default=0, nullable=False)
  statut_publication: str = Field(default="publie", max_length=20, nullable=False)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )

  def __repr__(self) -> str:
    return f"<CrascVideo: {self.titre}>"


class Evenement(SQLModel, table=True):
  """Représente un événement de l'agenda d'un CRASC."""
  title: str = Field(index=True, description="Titre de l'événement.")
  description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
  date_debut: datetime = Field(
    description="Date et heure de début de l'événement.",
    sa_column=Column(DateTime(timezone=True), nullable=False)
  )
  date_fin: Optional[datetime] = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True), nullable=True),
    description="Date et heure de fin (optionnelle)."
  )
  lieu: Optional[str] = Field(default=None, nullable=True, max_length=255, description="Lieu de l'événement.")

  crasc_id: Optional[int] = Field(default=None, nullable=True, foreign_key="crasc.id", ondelete="CASCADE")
  crasc: Optional[Crasc] = Relationship(back_populates="evenements")

  id: Optional[int] = Field(default=None, primary_key=True)
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )

  def __repr__(self) -> str:
    return f"<Événement: {self.title}>"
