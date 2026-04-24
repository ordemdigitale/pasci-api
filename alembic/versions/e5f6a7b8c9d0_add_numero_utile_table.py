"""add numero_utile table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'numero_utile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('categorie', sa.String(100), nullable=False),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('numero', sa.String(100), nullable=False),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column('ordre', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_numero_utile_categorie', 'numero_utile', ['categorie'])
    op.create_index('ix_numero_utile_ordre', 'numero_utile', ['ordre'])

    # Données initiales
    op.execute("""
    INSERT INTO numero_utile (categorie, label, numero, description, ordre, is_active) VALUES
    ('Urgences médicales', 'SAMU', '185', 'Service d''Aide Médicale Urgente', 1, true),
    ('Urgences médicales', 'Croix-Rouge de Côte d''Ivoire', '01 51 06 89', 'Assistance humanitaire', 2, true),
    ('Urgences médicales', 'CHU de Cocody', '22 48 16 07', NULL, 3, true),
    ('Urgences médicales', 'CHU de Treichville', '21 35 68 00', NULL, 4, true),
    ('Urgences médicales', 'CHU de Yopougon', '23 45 81 81', NULL, 5, true),
    ('Sécurité & Police', 'Police secours', '111', 'Numéro d''urgence national', 1, true),
    ('Sécurité & Police', 'Gendarmerie nationale', '170', NULL, 2, true),
    ('Sécurité & Police', 'Brigade anti-criminalité (BAC)', '110', NULL, 3, true),
    ('Sécurité & Police', 'Police judiciaire', '22 44 78 47', NULL, 4, true),
    ('Pompiers & Secours', 'Sapeurs-Pompiers', '180', 'Incendies et secours d''urgence', 1, true),
    ('Pompiers & Secours', 'Protection civile', '185', NULL, 2, true),
    ('Protection sociale & Enfance', 'Enfance en danger (SOS Enfants)', '116', 'Signalement maltraitance enfants', 1, true),
    ('Protection sociale & Enfance', 'Violences faites aux femmes', '1717', 'Ligne nationale d''écoute', 2, true),
    ('Protection sociale & Enfance', 'Ministère de la Femme', '20 21 81 22', NULL, 3, true),
    ('Protection sociale & Enfance', 'Direction Protection de l''Enfant', '20 21 76 65', NULL, 4, true),
    ('Services publics', 'CI-Énergie (panne électricité)', '100', NULL, 1, true),
    ('Services publics', 'SODECI (eau)', '20 30 60 00', NULL, 2, true),
    ('Services publics', 'Orange CI assistance', '888', NULL, 3, true),
    ('Services publics', 'MTN assistance', '188', NULL, 4, true),
    ('Services publics', 'Moov Africa assistance', '155', NULL, 5, true),
    ('Organisations de la société civile', 'PDOC — Plateforme OSC CRASC', '05 05 56 57 41', '15, avenue Jean Mermoz, Cocody', 1, true),
    ('Organisations de la société civile', 'Email PDOC', 'pdoc@plateforme-osci.org', 'Contact par email', 2, true),
    ('Organisations de la société civile', 'ONUCI — Bureau CI', '20 31 75 00', NULL, 3, true),
    ('Organisations de la société civile', 'PNUD Côte d''Ivoire', '20 31 49 00', NULL, 4, true),
    ('Urgences nationales', 'Numéro d''urgence européen (appel gratuit)', '112', NULL, 1, true),
    ('Urgences nationales', 'Centre antipoison', '20 21 32 11', NULL, 2, true),
    ('Urgences nationales', 'Cellule de crise nationale', '20 33 62 62', NULL, 3, true)
    """)


def downgrade() -> None:
    op.drop_index('ix_numero_utile_ordre', 'numero_utile')
    op.drop_index('ix_numero_utile_categorie', 'numero_utile')
    op.drop_table('numero_utile')
