# Model pour représenter les Partenaires Techniques et Financiers (PTF)
## app/models/ptf.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func, TEXT, ForeignKey, Integer
from sqlalchemy.event import listens_for
from typing import Optional, List
import slugify


class Ptf(SQLModel, table=True):
  """
    Represente un PTF dans la base de données.
  """
  id: Optional[int] = Field(default=None, primary_key=True)
  name: str = Field(index=True, unique=True)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)

  # Descriptions
  description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
  mission: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
  vision: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))

  # Images
  thumbnail_path: Optional[str] = Field(default="default.png", nullable=True, max_length=2048)
  cover_path: Optional[str] = Field(default=None, nullable=True, max_length=2048)

  # Informations de contact
  website: Optional[str] = Field(default=None, nullable=True, max_length=255)
  email: Optional[str] = Field(default=None, nullable=True, max_length=255)
  phone: Optional[str] = Field(default=None, nullable=True, max_length=50)
  address: Optional[str] = Field(default=None, nullable=True, max_length=500)

  # Informations générales
  pays: Optional[str] = Field(default=None, nullable=True, max_length=100)
  date_creation: Optional[str] = Field(default=None, nullable=True, max_length=50)

  # Domaines d'intervention (stocké en JSON)
  domaines: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))

  # define the relatioship from the parent side
  projets: List["Projet"] = Relationship(
    back_populates="ptf",
    sa_relationship_kwargs={"passive_deletes": True}
  )

  # Création automatique de slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)

  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Nom du PTF: {self.name}>"
  

class Projet(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  name: str = Field(nullable=False, unique=True, max_length=50)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)

  # Foreign key field
  # Use optional and set ondelete="SET NULL"
  ptf_id: Optional[int] = Field(default=None, foreign_key="ptf.id", ondelete="SET NULL")

  # Define the relationship from the child side
  # Add passive_deletes="all" in sa_relationship_kwargs to optimize for DB-Level handling
  ptf: Optional[Ptf] = Relationship(back_populates="projets")

  # Event listener for before insert to generate slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)