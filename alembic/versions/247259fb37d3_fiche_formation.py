"""formations : fiche complète et épinglage

Retours PdoC (6. Formations) : mode (en ligne, présentiel, hybride), durée en
heures, document délivré, compétences requises, lien de visioconférence,
chronogramme, et épinglage de 2 ou 3 formations en tête de page.

Revision ID: 247259fb37d3
Revises: b3c4d5e6f7a8
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "247259fb37d3"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("formations", sa.Column("lien_visio", sa.String(length=500), nullable=True))
    op.add_column("formations", sa.Column("mode", sa.String(length=20), nullable=True))
    op.add_column("formations", sa.Column("duree_heures", sa.Float(), nullable=True))
    op.add_column("formations", sa.Column("document_delivre", sa.String(length=20), nullable=True))
    op.add_column("formations", sa.Column("competences_requises", sa.TEXT(), nullable=True))
    op.add_column("formations", sa.Column("chronogramme", sa.TEXT(), nullable=True))
    op.add_column("formations", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    for colonne in ("is_pinned", "chronogramme", "competences_requises", "document_delivre",
                    "duree_heures", "mode", "lien_visio"):
        op.drop_column("formations", colonne)
