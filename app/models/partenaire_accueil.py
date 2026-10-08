# models/partenaire_accueil.py | Logos de la section « Nos partenaires » de l'accueil
from typing import Optional

from sqlmodel import SQLModel, Field


class PartenaireAccueil(SQLModel, table=True):
    __tablename__ = "partenaire_accueil"

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(max_length=200)
    # Fichier envoyé (UPLOAD_DIR) ou chemin du site web commençant par « / »
    logo_path: Optional[str] = Field(default=None, max_length=500)
    site_web: Optional[str] = Field(default=None, max_length=500)
    ordre: int = Field(default=0)
    actif: bool = Field(default=True)
