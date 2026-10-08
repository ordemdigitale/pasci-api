# models/task_force.py | Task forces thématiques regroupant des PTF
from typing import Optional

from sqlalchemy import TEXT, Column
from sqlmodel import Field, SQLModel


class TaskForcePtf(SQLModel, table=True):
    """PTF membre d'une task force (chef de file éventuel)."""
    __tablename__ = "task_force_ptf"

    task_force_id: int = Field(foreign_key="task_force.id", primary_key=True, ondelete="CASCADE")
    ptf_id: int = Field(foreign_key="ptf.id", primary_key=True, ondelete="CASCADE")
    chef_de_file: bool = Field(default=False)


class TaskForce(SQLModel, table=True):
    """Groupe de PTF travaillant sur une même thématique (genre, gouvernance, climat…)."""
    __tablename__ = "task_force"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(max_length=200, unique=True)
    slug: str = Field(max_length=200, unique=True, index=True)
    thematique: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(TEXT, nullable=True))
    ordre: int = Field(default=0)
    actif: bool = Field(default=True)
