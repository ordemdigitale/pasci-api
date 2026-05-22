"""add_osc_id_to_user

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS osc_id INTEGER REFERENCES osc(id) ON DELETE SET NULL'
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text('ALTER TABLE "user" DROP COLUMN IF EXISTS osc_id'))
