"""offres de projet : date limite de soumission ; task forces thématiques des PTF

Retours PdoC (section 9, Autres) :
- offres de projet : date limite de soumission (offre clôturée au-delà) ;
- annuaire PTF : task forces thématiques (tables task_force et
  task_force_ptf) ; la classification par types utilise le champ
  ptf.categorie existant.

Revision ID: 9ab13c5d7e64
Revises: 8fa02b4c6d53
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9ab13c5d7e64"
down_revision: Union[str, None] = "8fa02b4c6d53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("offreprojet", sa.Column("date_limite_soumission", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "task_force",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nom", sa.String(length=200), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=200), nullable=False, unique=True),
        sa.Column("thematique", sa.String(length=200), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_task_force_slug", "task_force", ["slug"])
    op.create_table(
        "task_force_ptf",
        sa.Column("task_force_id", sa.Integer(), sa.ForeignKey("task_force.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ptf_id", sa.Integer(), sa.ForeignKey("ptf.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chef_de_file", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("task_force_ptf")
    op.drop_index("ix_task_force_slug", table_name="task_force")
    op.drop_table("task_force")
    op.drop_column("offreprojet", "date_limite_soumission")
