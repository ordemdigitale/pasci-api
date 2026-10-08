"""formations : supports de formation et évaluation finale

Retours PdoC (section 6, Formations) et test du parcours complet :
- « lucarne » des supports de formation : table formation_support
  (documents à télécharger ou liens, réservés aux inscrits sauf s'ils sont
  publics) ;
- évaluation avant la délivrance du certificat : formations.note_minimale,
  tables formation_question (QCM) et formation_tentative.

Revision ID: 5c7d9e1f3a20
Revises: f7a8b9c0d1e2
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5c7d9e1f3a20"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("formations", sa.Column("note_minimale", sa.Integer(), nullable=False, server_default="70"))

    op.create_table(
        "formation_support",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("formation_id", sa.Integer(), sa.ForeignKey("formations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=False, server_default="fichier"),
        sa.Column("chemin", sa.String(length=500), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("nom_original", sa.String(length=255), nullable=True),
        sa.Column("taille", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_formation_support_formation_id", "formation_support", ["formation_id"])

    op.create_table(
        "formation_question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("formation_id", sa.Integer(), sa.ForeignKey("formations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enonce", sa.TEXT(), nullable=False),
        sa.Column("choix", sa.TEXT(), nullable=False),
        sa.Column("bonnes_reponses", sa.TEXT(), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_formation_question_formation_id", "formation_question", ["formation_id"])

    op.create_table(
        "formation_tentative",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inscription_id", sa.Integer(), sa.ForeignKey("formation_inscription.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reussi", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reponses", sa.TEXT(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_formation_tentative_inscription_id", "formation_tentative", ["inscription_id"])


def downgrade() -> None:
    op.drop_index("ix_formation_tentative_inscription_id", table_name="formation_tentative")
    op.drop_table("formation_tentative")
    op.drop_index("ix_formation_question_formation_id", table_name="formation_question")
    op.drop_table("formation_question")
    op.drop_index("ix_formation_support_formation_id", table_name="formation_support")
    op.drop_table("formation_support")
    op.drop_column("formations", "note_minimale")
