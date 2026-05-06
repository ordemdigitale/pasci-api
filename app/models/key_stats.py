# models/key_stats.py
from sqlmodel import SQLModel, Field
from typing import Optional


class KeyStats(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  name: str = Field(nullable=False, unique=True, max_length=50)
  number: Optional[int] = Field(default=0, nullable=True)

  # Representation in admin/logs
  def __repr__(self) -> str:
    return f"<Chiffre clé: {self.name}>"