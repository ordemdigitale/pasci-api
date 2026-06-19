"""add osc formalisation document

Revision ID: a7b8c9d0e1f2
Revises: a6b7c8d9e0f1
Create Date: 2026-06-18 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "osc",
        sa.Column("document_formalisation_path", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "demande_adhesion",
        sa.Column("document_formalisation_path", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("demande_adhesion", "document_formalisation_path")
    op.drop_column("osc", "document_formalisation_path")
