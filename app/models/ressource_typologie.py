# models/ressource_typologie.py | Typologie des ressources (types et catégories gérés dans l'admin)
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field


class RessourceType(SQLModel, table=True):
    """
    Type de ressource (livres, périodiques, documents officiels…).
    `slug` est la valeur stockée dans Documentation.type : il ne change pas
    après création ; seul le libellé (`nom`) est modifiable.
    """
    __tablename__ = "ressource_type"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=50, unique=True, index=True)
    nom: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    ordre: int = Field(default=0)
    actif: bool = Field(default=True)


class RessourceCategorie(SQLModel, table=True):
    """
    Catégorie détaillée (romans, BD, lois, dictionnaires…). `type_slug` la
    rattache à un type ; sans type, elle est proposée pour tous les types.
    Son `nom` est la valeur stockée dans Documentation.category.
    """
    __tablename__ = "ressource_categorie"
    __table_args__ = (UniqueConstraint("nom", "type_slug", name="uq_ressource_categorie_nom_type"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(max_length=100)
    type_slug: Optional[str] = Field(default=None, max_length=50, index=True)
    ordre: int = Field(default=0)
    actif: bool = Field(default=True)
