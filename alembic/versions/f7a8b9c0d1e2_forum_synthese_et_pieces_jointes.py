"""forum : synthèse des discussions et messages multimédias

Retours PdoC (pôles de concertation) :
- synthèse : une discussion peut être close et recevoir une synthèse
  (forum_sujet.est_clos, synthese, synthese_par, synthese_le) ;
- messagerie multimédia : photos, audio et vidéos joints aux sujets et aux
  messages (table forum_piece_jointe).

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("forum_sujet", sa.Column("est_clos", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("forum_sujet", sa.Column("synthese", sa.TEXT(), nullable=True))
    op.add_column("forum_sujet", sa.Column("synthese_par", sa.String(length=200), nullable=True))
    op.add_column("forum_sujet", sa.Column("synthese_le", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "forum_piece_jointe",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sujet_id", sa.Integer(), sa.ForeignKey("forum_sujet.id", ondelete="CASCADE"), nullable=True),
        sa.Column("commentaire_id", sa.Integer(), sa.ForeignKey("forum_commentaire.id", ondelete="CASCADE"), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("chemin", sa.String(length=500), nullable=False),
        sa.Column("nom_original", sa.String(length=255), nullable=True),
        sa.Column("mime", sa.String(length=100), nullable=True),
        sa.Column("taille", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forum_piece_jointe_sujet_id", "forum_piece_jointe", ["sujet_id"])
    op.create_index("ix_forum_piece_jointe_commentaire_id", "forum_piece_jointe", ["commentaire_id"])


def downgrade() -> None:
    op.drop_index("ix_forum_piece_jointe_commentaire_id", table_name="forum_piece_jointe")
    op.drop_index("ix_forum_piece_jointe_sujet_id", table_name="forum_piece_jointe")
    op.drop_table("forum_piece_jointe")
    for col in ("synthese_le", "synthese_par", "synthese", "est_clos"):
        op.drop_column("forum_sujet", col)
