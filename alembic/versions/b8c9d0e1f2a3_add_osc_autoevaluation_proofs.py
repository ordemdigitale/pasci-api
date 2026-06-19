"""add osc autoevaluation proofs

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROOF_COLUMNS = (
    sa.Column("plan_action_document_path", sa.String(length=2048), nullable=True),
    sa.Column("rapports_annuels_document_path", sa.String(length=2048), nullable=True),
    sa.Column("adhesion_crasc_document_path", sa.String(length=2048), nullable=True),
)


def upgrade() -> None:
    for table_name in ("osc", "demande_adhesion"):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            for column in PROOF_COLUMNS:
                batch_op.add_column(column.copy())


def downgrade() -> None:
    for table_name in ("demande_adhesion", "osc"):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_column("adhesion_crasc_document_path")
            batch_op.drop_column("rapports_annuels_document_path")
            batch_op.drop_column("plan_action_document_path")
