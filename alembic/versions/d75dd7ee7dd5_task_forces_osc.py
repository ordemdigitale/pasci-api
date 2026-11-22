"""task forces de l'espace collaboratif : groupes d'OSC

Retour PdoC : « les task forces sont dans le forum, et ce sont des OSC ».
La table task_force existante regroupe des PTF et alimente l'annuaire des
partenaires : elle reste inchangée. Nouvelle entité task_force_osc, rattachée
à l'espace collaboratif, dont les membres sont des OSC de l'annuaire.

Revision ID: d75dd7ee7dd5
Revises: 86982d9c1656
Create Date: 2026-11-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d75dd7ee7dd5"
down_revision: Union[str, None] = "86982d9c1656"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_force_osc",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=True),
        sa.Column("thematique", sa.String(length=200), nullable=True),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("pole_id", sa.Integer(), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["pole_id"], ["pole_concertation.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nom"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_task_force_osc_slug"), "task_force_osc", ["slug"])

    op.create_table(
        "task_force_osc_membre",
        sa.Column("task_force_id", sa.Integer(), nullable=False),
        sa.Column("osc_id", sa.Integer(), nullable=False),
        sa.Column("chef_de_file", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["task_force_id"], ["task_force_osc.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["osc_id"], ["osc.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_force_id", "osc_id"),
    )


def downgrade() -> None:
    op.drop_table("task_force_osc_membre")
    op.drop_index(op.f("ix_task_force_osc_slug"), table_name="task_force_osc")
    op.drop_table("task_force_osc")
