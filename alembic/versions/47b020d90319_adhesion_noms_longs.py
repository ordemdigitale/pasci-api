"""adhésion : noms d'organisation longs

Retour PdoC : « lorsqu'une OSC s'inscrit et que son nom est long, ça ne
passe pas ». demande_adhesion.nom_organisation était plafonné à 200
caractères alors que l'annuaire contient déjà des noms de 219 caractères :
PostgreSQL rejetait l'enregistrement et le formulaire échouait sans
indication. Le nom devient un TEXT ; les autres champs de saisie libre sont
élargis et alignés sur les colonnes correspondantes de l'annuaire.

Revision ID: 47b020d90319
Revises: d2bccc1c3c0a
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "47b020d90319"
down_revision: Union[str, None] = "d2bccc1c3c0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, colonne, nouveau type, ancien type)
ELARGISSEMENTS = [
    ("demande_adhesion", "nom_organisation", sa.TEXT(), sa.String(length=200)),
    ("demande_adhesion", "sigle", sa.String(length=200), sa.String(length=100)),
    ("demande_adhesion", "type_organisation", sa.String(length=200), sa.String(length=100)),
    ("demande_adhesion", "type_osc", sa.String(length=200), sa.String(length=100)),
    ("demande_adhesion", "region", sa.String(length=200), sa.String(length=100)),
    ("demande_adhesion", "departement", sa.String(length=200), sa.String(length=150)),
    ("demande_adhesion", "sous_prefecture", sa.String(length=200), sa.String(length=150)),
    ("demande_adhesion", "ville", sa.String(length=200), sa.String(length=100)),
    ("demande_adhesion", "email", sa.String(length=255), sa.String(length=200)),
    ("demande_adhesion", "categorie", sa.String(length=200), sa.String(length=100)),
    ("osc", "sigle", sa.String(length=200), sa.String(length=100)),
    ("osc", "region_nom", sa.String(length=200), sa.String(length=150)),
    ("osc", "departement", sa.String(length=200), sa.String(length=150)),
    ("osc", "sous_prefecture", sa.String(length=200), sa.String(length=150)),
]


def upgrade() -> None:
    for table, colonne, nouveau, _ in ELARGISSEMENTS:
        op.alter_column(table, colonne, type_=nouveau, existing_nullable=True)


def downgrade() -> None:
    # Les valeurs plus longues que l'ancienne limite seraient tronquées.
    for table, colonne, _, ancien in ELARGISSEMENTS:
        op.alter_column(
            table,
            colonne,
            type_=ancien,
            existing_nullable=True,
            postgresql_using=f"left({colonne}, {ancien.length})",
        )
