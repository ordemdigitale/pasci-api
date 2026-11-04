"""actualités : auteur (point focal communication)

Retours PdoC (Backend/Formulaire de saisie des Actualités) : « lorsqu'un
article est rejeté, l'article rejeté doit aller dans l'email du point focal
communication ». news.auteur_id : compte qui a rédigé l'actualité (rédacteur
CRASC ou compte OSC), destinataire de l'email de rejet.

Revision ID: 55653a22eaa6
Revises: d9c1e44862aa
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "55653a22eaa6"
down_revision: Union[str, None] = "d9c1e44862aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news", sa.Column("auteur_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("news_auteur_id_fkey", "news", "user", ["auteur_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("news_auteur_id_fkey", "news", type_="foreignkey")
    op.drop_column("news", "auteur_id")
