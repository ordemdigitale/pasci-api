from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
import slugify

# Parent model
class Team(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  name: str = Field(nullable=False, unique=True, max_length=50)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)

  # define the relatioship from the parent side
  heroes: List["Hero"] = Relationship(
    back_populates="team",
    sa_relationship_kwargs={"passive_deletes": True}
  )

  # Event listener for before insert to generate slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)

# Child model
class Hero(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  name: str = Field(nullable=False, unique=True, max_length=50)
  slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)

  # Foreign key field
  # Use optional and set ondelete="SET NULL"
  team_id: Optional[int] = Field(default=None, foreign_key="team.id", ondelete="SET NULL")

  # Define the relationship from the child side
  # Add passive_deletes="all" in sa_relationship_kwargs to optimize for DB-Level handling
  team: Optional[Team] = Relationship(back_populates="heroes")

  # Event listener for before insert to generate slug
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.name and not self.slug:
      self.slug = slugify.slugify(self.name)