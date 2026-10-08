"""accueil : expiration et descriptif des slides, partenaires gérés dans l'admin

Retours PdoC (Accueil) :
- 1.1 / 1.3 : date d'expiration des slides (haut et bas), désactivation
  automatique au-delà ;
- 1.2 : descriptif propre à chaque slide pour « Voir plus » (objectif,
  résumé, photo 1, photo 2, article) ;
- 1.8 : section « Nos partenaires » gérée dans l'admin (table
  partenaire_accueil), reprenant les 4 logos existants et ajoutant AICS.

Revision ID: 8fa02b4c6d53
Revises: 7e9f1a3b5c42
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8fa02b4c6d53"
down_revision: Union[str, None] = "7e9f1a3b5c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PARTENAIRES = [
    # (nom, logo — chemin du site web, site : à compléter dans l'admin)
    ("Save The Children", "/images/partenaires/save-the-children.png", None),
    ("CERAP", "/images/partenaires/cerap.png", None),
    ("Social Justice", "/images/partenaires/social-justice.png", None),
    ("Union Européenne", "/images/partenaires/union-europeenne.png", None),
    # Logo officiel à téléverser depuis l'admin (Accueil › Partenaires)
    ("AICS", None, "https://www.aics.gov.it"),
]


def upgrade() -> None:
    op.add_column("hero_slide", sa.Column("date_expiration", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hero_slide", sa.Column("objectif", sa.TEXT(), nullable=True))
    op.add_column("hero_slide", sa.Column("resume", sa.TEXT(), nullable=True))
    op.add_column("hero_slide", sa.Column("article", sa.TEXT(), nullable=True))
    op.add_column("hero_slide", sa.Column("photo1_path", sa.String(length=500), nullable=True))
    op.add_column("hero_slide", sa.Column("photo2_path", sa.String(length=500), nullable=True))

    partenaires = op.create_table(
        "partenaire_accueil",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("logo_path", sa.String(length=500), nullable=True),
        sa.Column("site_web", sa.String(length=500), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.bulk_insert(partenaires, [
        {"nom": nom, "logo_path": logo, "site_web": site, "ordre": i, "actif": True}
        for i, (nom, logo, site) in enumerate(PARTENAIRES)
    ])


def downgrade() -> None:
    op.drop_table("partenaire_accueil")
    for col in ("photo2_path", "photo1_path", "article", "resume", "objectif", "date_expiration"):
        op.drop_column("hero_slide", col)
