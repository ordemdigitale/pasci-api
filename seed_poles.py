"""
Script pour créer les 11 pôles de concertation dans la base de données.
Usage: uv run python seed_poles.py
"""
import asyncio
import json
from app.database.session import async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as AlcSession
import slugify as slugify_lib

# Import models to register metadata
import app.models.users
import app.models.crasc
import app.models.jobs
import app.models.key_stats
import app.models.ptf
import app.models.hero
import app.models.tags
import app.models.formation
import app.models.documentation
import app.models.offre_projet
import app.models.forum
from app.models.forum import PoleConcertation

POLES = [
    {
        "name": "Pôle Agriculture",
        "category": "Agriculture, Sylviculture et Pêche",
        "description": "Espace de discussion et d'échange pour les OSC du secteur agricole. Agir ensemble pour l'autosuffisance alimentaire, autonomiser les femmes et les jeunes agriculteurs.",
        "objectifs": json.dumps([
            "Agir pour autonomiser les femmes et les jeunes agriculteurs",
            "Maîtriser nos productions et agir ensemble pour l'autosuffisance alimentaire",
            "Partager nos expériences et transformer nos échecs individuels",
        ]),
        "image_path": "/images/espace-collabo/2d5632f9-ac11-4f20-8029-a58de61ba137.jpg",
    },
    {
        "name": "Pôle Éducation",
        "category": "Education",
        "description": "Espace dédié aux OSC œuvrant dans le domaine de l'éducation, de la formation et de l'alphabétisation.",
        "objectifs": json.dumps([
            "Améliorer l'accès à une éducation de qualité pour tous",
            "Soutenir l'alphabétisation des adultes",
            "Renforcer les capacités des acteurs de l'éducation",
        ]),
        "image_path": "/images/espace-collabo/63ac2eed-9ce3-4108-bad4-c7cf536795da.jpg",
    },
    {
        "name": "Pôle Commerce et Tourisme",
        "category": "Commerce et Tourisme",
        "description": "Forum pour les OSC actives dans le commerce, l'artisanat et le tourisme local.",
        "objectifs": json.dumps([
            "Promouvoir le commerce local et l'artisanat",
            "Développer l'écotourisme communautaire",
            "Faciliter l'accès aux marchés pour les petits producteurs",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Santé",
        "category": "Santé",
        "description": "Espace d'échanges pour les OSC œuvrant dans la santé communautaire, la prévention et l'accès aux soins.",
        "objectifs": json.dumps([
            "Améliorer l'accès aux soins de santé primaires",
            "Renforcer la prévention des maladies",
            "Soutenir la santé maternelle et infantile",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Environnement",
        "category": "Environnement et Développement Durable",
        "description": "Forum dédié aux OSC engagées dans la protection de l'environnement et le développement durable.",
        "objectifs": json.dumps([
            "Sensibiliser à la protection de l'environnement",
            "Promouvoir les énergies renouvelables",
            "Lutter contre la déforestation et la désertification",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Genre et Droits",
        "category": "Genre, Droits Humains et Gouvernance",
        "description": "Espace de discussion pour les OSC travaillant sur le genre, les droits humains et la bonne gouvernance.",
        "objectifs": json.dumps([
            "Promouvoir l'égalité de genre et l'autonomisation des femmes",
            "Défendre les droits humains fondamentaux",
            "Renforcer la participation citoyenne",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Jeunesse",
        "category": "Jeunesse et Sport",
        "description": "Forum pour les OSC œuvrant pour la jeunesse, l'emploi des jeunes et le sport communautaire.",
        "objectifs": json.dumps([
            "Favoriser l'insertion professionnelle des jeunes",
            "Promouvoir le sport comme vecteur de cohésion sociale",
            "Développer l'entrepreneuriat jeune",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Culture et Arts",
        "category": "Culture, Arts et Patrimoine",
        "description": "Espace d'échanges pour les OSC culturelles, artistiques et de préservation du patrimoine.",
        "objectifs": json.dumps([
            "Valoriser les cultures et traditions locales",
            "Soutenir les artistes et artisans",
            "Préserver le patrimoine culturel immatériel",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Numérique",
        "category": "Numérique et Innovation",
        "description": "Forum pour les OSC actives dans la transformation numérique, l'innovation sociale et les TIC.",
        "objectifs": json.dumps([
            "Réduire la fracture numérique",
            "Promouvoir l'innovation sociale par le numérique",
            "Former les communautés aux outils numériques",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Eau et Assainissement",
        "category": "Eau, Hygiène et Assainissement",
        "description": "Espace dédié aux OSC travaillant sur l'accès à l'eau potable et l'assainissement.",
        "objectifs": json.dumps([
            "Améliorer l'accès à l'eau potable en zones rurales",
            "Promouvoir l'hygiène et l'assainissement",
            "Renforcer la gestion communautaire des ressources en eau",
        ]),
        "image_path": None,
    },
    {
        "name": "Pôle Économie Sociale",
        "category": "Économie Sociale et Solidaire",
        "description": "Forum pour les OSC actives dans l'économie sociale, les coopératives et la microfinance.",
        "objectifs": json.dumps([
            "Développer les coopératives et mutuelles communautaires",
            "Faciliter l'accès au microcrédit",
            "Promouvoir l'entrepreneuriat social",
        ]),
        "image_path": None,
    },
]


async def seed():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AlcSession(async_engine) as session:
        for pole_data in POLES:
            # Check if already exists
            result = await session.execute(
                select(PoleConcertation).where(PoleConcertation.name == pole_data["name"])
            )
            existing = result.scalars().first()
            if existing:
                print(f"✓ Déjà existant: {pole_data['name']}")
                continue

            pole = PoleConcertation(
                name=pole_data["name"],
                category=pole_data["category"],
                description=pole_data["description"],
                objectifs=pole_data["objectifs"],
                image_path=pole_data.get("image_path"),
                slug=slugify_lib.slugify(pole_data["name"]),
            )
            session.add(pole)
            print(f"✅ Créé: {pole_data['name']}")

        await session.commit()
    print("\n🎉 Seed terminé ! 11 pôles de concertation créés.")


if __name__ == "__main__":
    asyncio.run(seed())
