# models/crasc.py (Model name CRASC + related models)
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.event import listens_for
from typing import Optional, List
import slugify, re

# Base tables (lookup tables to avoid circular imports)
class CrascRegion(SQLModel, table=True):
  """ Represents a CRASC region in the database. """
  id: int = Field(default=None, primary_key=True)
  name: str = Field(nullable=False, max_length=100, unique=True, description="Nom de la région CRASC")
  description: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True, description="Slug de la région CRASC")
  order: Optional[int] = Field(default=None, nullable=True, description="Ordre d'affichage de la région CRASC")
  osc_count: Optional[int] = Field(default=0, nullable=True, description="Nombre d'OSCs dans cette région CRASC")

  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )
  # Relationships
  regions_civ: List["RegionCiv"] = Relationship(back_populates="crasc_region")
  oscs: List["Osc"] = Relationship(back_populates="region_crasc")
  news_items: List["News"] = Relationship(back_populates="crasc")

  # Event listener for before insert to generate slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)

  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Région CRASC: {self.name}>"


class RegionCiv(SQLModel, table=True):
  """ Représente une région administrative de la Côte d'Ivoire dans la base de données. """
  id: int = Field(default=None, primary_key=True)
  name: str = Field(nullable=False, max_length=100, unique=True, description="Nom d'une région de la Côte d'Ivoire")
  # Foreign key to CrascRegion
  crasc_region_id: int = Field(foreign_key="crascregion.id")
  # Relationship: one RegionCiv belongs to one CrascRegion
  crasc_region: CrascRegion = Relationship(back_populates="regions_civ")

  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )

  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Région de la Côte d'Ivoire: {self.name}>"


class OscType(SQLModel, table=True):
  """ Represents a type of OSC in the database. """
  id: int = Field(default=None, primary_key=True)
  name: str = Field(index=True, unique=True)
  description: Optional[str] = None
  oscs: List["Osc"] = Relationship(back_populates="type_osc")
  
  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Type de OSC: {self.name}>"
  

class Osc(SQLModel, table=True):
  """ Represents an OSC (Organisation de la Société Civile) in the database. """
  id: int = Field(default=None, primary_key=True)
  name: str = Field(index=True, unique=True)
  description: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

  type_id: int = Field(foreign_key="osctype.id")
  type_osc: OscType = Relationship(back_populates="oscs")

  region_id: int = Field(foreign_key="crascregion.id") # To link to CRASC regions. Later change it to crasc_id
  region_crasc: CrascRegion = Relationship(back_populates="oscs") # Later change it to crasc_region

  latitude: Optional[float] = None
  longitude: Optional[float] = None
  address: Optional[str] = None

  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )

  # Relationships
  news_articles: List["NewsArticles"] = Relationship(back_populates="osc")
  news_items: List["News"] = Relationship(back_populates="osc")

  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Nome de l'OSC: {self.name}>"
  

class NewsArticles(SQLModel, table=True):
   """ Represents a news article in the database. """
   id: int = Field(default=None, primary_key=True, index=True, description="Unique news article identifier")
   # Core News Information
   title: str = Field(max_length=250, nullable=False, description="Title of the news article")
   content: str = Field(sa_column=Column(String, nullable=True), description="Content of the news article")
   preview_text: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True), description="Preview text of the article")
   author: Optional[str] = Field(default=None, max_length=100)
   publication_date: Optional[datetime] = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now()),
   )
   image_url: Optional[str] = Field(default=None, max_length=2048, description="ImageKit public URL")

   osc_id: int = Field(foreign_key="osc.id")
   osc: Osc = Relationship(back_populates="news_articles")

   # Status Fields
   is_published: bool = Field(default=False)
   status: str = Field(default="draft", max_length=20) # e.g., 'draft', 'published', 'archived'

   # Timestamps (auto-managed)
   created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc),
      sa_column=Column(DateTime(timezone=True), server_default=func.now()),
   )
   updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
  )
   
   # Representation in admin/logs
   def __repr__(self) -> str:
      return f"<NewsArticle: {self.title}>"
   
##############
# News Model #
class News(SQLModel, table=True):
  id: int = Field(default=None, primary_key=True, index=True, description="Identifiant unique de l'actualité.")
  title: str = Field(max_length=250, nullable=False, description="Titre de l'actualité.")
  
  # Optional Foreign Keys
  osc_id: Optional[int] = Field(default=None, nullable=True, foreign_key="osc.id")
  crasc_id: Optional[int] = Field(default=None, nullable=True, foreign_key="crascregion.id")
  
  # Relationships
  # These allow you to access news.osc or news.crasc directly
  osc: Optional[Osc] = Relationship(back_populates="news_items")
  crasc: Optional[CrascRegion] = Relationship(back_populates="news_items")