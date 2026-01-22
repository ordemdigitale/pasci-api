# models/crasc.py (Model name CRASC + related models)
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func, TEXT, ForeignKey, Integer
from sqlalchemy.event import listens_for
from typing import Optional, List
import slugify, re


class Crasc(SQLModel, table=True):
  """ Represente un CRASC dans la base de données. """
  name: str = Field(nullable=False, max_length=100, unique=True, description="Nom du CRASC.")
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
  description: Optional[str] = Field(default=None, nullable=True, max_length=100)
  osc_count: Optional[int] = Field(default=0, nullable=True, description="Nombre d'OSCs membre du CRASC")

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
  description: Optional[str] = Field(default=None, nullable=True, max_length=100)
  thumbnail_path: Optional[str] = Field(default="default.png", nullable=True, max_length=2048)
  
  type_id: Optional[int] = Field(default=None, foreign_key="osctype.id", ondelete="SET NULL")
  type: Optional[OscType] = Relationship(back_populates="oscs")

  crasc_id: Optional[int] = Field(default=None, foreign_key="crasc.id", ondelete="SET NULL")
  crasc: Optional[Crasc] = Relationship(back_populates="oscs")

  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None

  news_items: List["News"] = Relationship(
    back_populates="osc",
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
    if self.title and not self.slug:
      self.slug = slugify.slugify(self.title)
  
  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Titre: {self.title}>"