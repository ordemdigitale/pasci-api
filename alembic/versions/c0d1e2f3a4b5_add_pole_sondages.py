"""add pole sondages

Revision ID: c0d1e2f3a4b5
Revises: b0c1d2e3f4a5
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pole_sondage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pole_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("results_visibility", sa.String(length=20), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pole_id"], ["pole_concertation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pole_sondage_option",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sondage_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["sondage_id"], ["pole_sondage.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pole_sondage_vote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sondage_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("osc_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["option_id"], ["pole_sondage_option.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["osc_id"], ["osc.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sondage_id"], ["pole_sondage.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sondage_id", "user_id", name="uq_pole_sondage_vote_user"),
    )
    op.create_index("ix_pole_sondage_vote_user_id", "pole_sondage_vote", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_pole_sondage_vote_user_id", table_name="pole_sondage_vote")
    op.drop_table("pole_sondage_vote")
    op.drop_table("pole_sondage_option")
    op.drop_table("pole_sondage")
