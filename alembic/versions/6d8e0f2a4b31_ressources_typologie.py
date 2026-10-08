"""ressources : typologie et catégories gérées dans l'admin

Retours PdoC (section 7, Ressources) :
- typologie enrichie (livres, périodiques, ouvrages de référence, documents
  officiels, fiches/modules PdoC) : table ressource_type ;
- catégories détaillées (romans, BD, poésie, théâtre, revues, dictionnaires,
  lois…) : table ressource_categorie, rattachées ou non à un type.
Les valeurs déjà utilisées (types documentation/fiche et les 9 catégories
historiques) sont conservées : aucun document existant n'est modifié.

Revision ID: 6d8e0f2a4b31
Revises: 5c7d9e1f3a20
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6d8e0f2a4b31"
down_revision: Union[str, None] = "5c7d9e1f3a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TYPES = [
    # (slug, nom, description)
    ("documentation", "Documentation", "Rapports, guides, études, manuels…"),
    ("fiche", "Fiches et modules PdoC", "Fiches informatives et modules produits par la PdoC"),
    ("livre", "Livres", "Romans, bandes dessinées, poésie, théâtre, essais…"),
    ("periodique", "Périodiques", "Revues, magazines, journaux, bulletins"),
    ("ouvrage-reference", "Ouvrages de référence", "Dictionnaires, encyclopédies, annuaires, atlas"),
    ("document-officiel", "Documents officiels", "Lois, décrets, arrêtés, codes, conventions"),
]

CATEGORIES = {
    # Catégories historiques : proposées pour tous les types (documents existants)
    None: ["Rapport", "Guide", "Étude", "Manuel", "PV", "Infographie", "Politique", "Récit", "Plan"],
    "fiche": ["Fiche pratique", "Fiche thématique", "Module de formation"],
    "livre": ["Roman", "Bande dessinée", "Poésie", "Théâtre", "Essai", "Contes et nouvelles", "Biographie"],
    "periodique": ["Revue", "Magazine", "Journal", "Bulletin", "Lettre d'information"],
    "ouvrage-reference": ["Dictionnaire", "Encyclopédie", "Annuaire", "Atlas", "Glossaire"],
    "document-officiel": ["Loi", "Décret", "Arrêté", "Ordonnance", "Code", "Circulaire",
                          "Convention et traité", "Journal officiel"],
}


def upgrade() -> None:
    types = op.create_table(
        "ressource_type",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_ressource_type_slug", "ressource_type", ["slug"], unique=True)

    categories = op.create_table(
        "ressource_categorie",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("type_slug", sa.String(length=50), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("nom", "type_slug", name="uq_ressource_categorie_nom_type"),
    )
    op.create_index("ix_ressource_categorie_type_slug", "ressource_categorie", ["type_slug"])

    op.bulk_insert(types, [
        {"slug": s, "nom": n, "description": d, "ordre": i, "actif": True}
        for i, (s, n, d) in enumerate(TYPES)
    ])
    op.bulk_insert(categories, [
        {"nom": nom, "type_slug": type_slug, "ordre": i, "actif": True}
        for type_slug, noms in CATEGORIES.items()
        for i, nom in enumerate(noms)
    ])

    # Types et catégories déjà présents dans les documents mais absents de la liste
    # (saisis librement auparavant) : ajoutés pour rester sélectionnables.
    op.execute(
        """
        INSERT INTO ressource_type (slug, nom, ordre, actif)
        SELECT DISTINCT d.type, initcap(replace(d.type, '-', ' ')), 100, true
        FROM documentation d
        WHERE d.type IS NOT NULL AND d.type <> ''
          AND NOT EXISTS (SELECT 1 FROM ressource_type t WHERE t.slug = d.type)
        """
    )
    op.execute(
        """
        INSERT INTO ressource_categorie (nom, type_slug, ordre, actif)
        SELECT DISTINCT d.category, NULL::varchar, 100, true
        FROM documentation d
        WHERE d.category IS NOT NULL AND d.category <> ''
          AND NOT EXISTS (SELECT 1 FROM ressource_categorie c WHERE c.nom = d.category)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ressource_categorie_type_slug", table_name="ressource_categorie")
    op.drop_table("ressource_categorie")
    op.drop_index("ix_ressource_type_slug", table_name="ressource_type")
    op.drop_table("ressource_type")
