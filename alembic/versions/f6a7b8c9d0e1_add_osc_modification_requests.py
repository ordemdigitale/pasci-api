"""add OSC modification requests

Revision ID: f6a7b8c9d0e1
Revises: b8c9d0e1f2a3
Create Date: 2026-06-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "osc_modification_request",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("osc_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("pole_ids", sa.JSON(), nullable=True),
        sa.Column("requested_by_id", sa.String(length=80), nullable=True),
        sa.Column("reviewed_by_id", sa.String(length=80), nullable=True),
        sa.Column("review_comment", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["osc_id"], ["osc.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_osc_modification_request_osc_id", "osc_modification_request", ["osc_id"], unique=False)
    op.create_index("ix_osc_modification_request_status", "osc_modification_request", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_osc_modification_request_status", table_name="osc_modification_request")
    op.drop_index("ix_osc_modification_request_osc_id", table_name="osc_modification_request")
    op.drop_table("osc_modification_request")
