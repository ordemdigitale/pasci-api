"""add crasc_video, catalogue_formation, email_pca

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f7
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa

revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Champ email_pca sur la table crasc
    conn.execute(sa.text(
        "ALTER TABLE crasc ADD COLUMN IF NOT EXISTS email_pca VARCHAR(200)"
    ))

    # 2. Table crasc_video
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS crasc_video (
            id SERIAL PRIMARY KEY,
            crasc_id INTEGER NOT NULL REFERENCES crasc(id) ON DELETE CASCADE,
            titre VARCHAR(200) NOT NULL,
            url VARCHAR(500) NOT NULL,
            description TEXT,
            ordre INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))

    # 3. Table catalogue_formation
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS catalogue_formation (
            id SERIAL PRIMARY KEY,
            titre VARCHAR(200) NOT NULL,
            description TEXT,
            fichier_path VARCHAR(500) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))


def downgrade():
    op.drop_table('catalogue_formation')
    op.drop_table('crasc_video')
    op.drop_column('crasc', 'email_pca')
