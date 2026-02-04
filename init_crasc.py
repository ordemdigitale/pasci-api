#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour initialiser les CRASC dans la base de données
"""
import asyncio
from app.database.session import get_db
from app.models.crasc import Crasc
from app.models.formation import Formation
from app.models.documentation import Documentation
from sqlmodel import select

# Données des CRASC (basé sur les 5 régions de la Côte d'Ivoire)
CRASC_DATA = [
    {
        "name": "CRASC SUD",
        "slug": "crasc-sud",
        "description": "Coordination Régionale des Acteurs de la Société Civile du Sud de la Côte d'Ivoire. Cette coordination regroupe les OSC des régions du Sud Comoé, Agnéby-Tiassa, Grands-Ponts, Lagunes, et Me.",
        "osc_count": 0
    },
    {
        "name": "CRASC CENTRE",
        "slug": "crasc-centre",
        "description": "Coordination Régionale des Acteurs de la Société Civile du Centre de la Côte d'Ivoire. Cette coordination couvre les régions du Bélier, Iffou, Moronou, N'Zi, et Lacs.",
        "osc_count": 0
    },
    {
        "name": "CRASC NORD",
        "slug": "crasc-nord",
        "description": "Coordination Régionale des Acteurs de la Société Civile du Nord de la Côte d'Ivoire. Cette coordination regroupe les OSC des régions de Bounkani, Poro, Tchologo, Bagoué, et Hambol.",
        "osc_count": 0
    },
    {
        "name": "CRASC EST",
        "slug": "crasc-est",
        "description": "Coordination Régionale des Acteurs de la Société Civile de l'Est de la Côte d'Ivoire. Cette coordination couvre les régions de l'Indénié-Djuablin, Gontougo, et Bounkani.",
        "osc_count": 0
    },
    {
        "name": "CRASC OUEST",
        "slug": "crasc-ouest",
        "description": "Coordination Régionale des Acteurs de la Société Civile de l'Ouest de la Côte d'Ivoire. Cette coordination regroupe les OSC des régions du Guémon, Cavally, Tonkpi, Bafing, et Montagnes.",
        "osc_count": 0
    }
]


async def init_crasc():
    """Initialise les CRASC dans la base de données"""
    async for db in get_db():
        try:
            print("🚀 Initialisation des CRASC...")

            # Vérifier si des CRASC existent déjà
            result = await db.execute(select(Crasc))
            existing_crasc = result.scalars().all()

            if existing_crasc:
                print(f"ℹ️  {len(existing_crasc)} CRASC trouvés dans la base de données.")
                print("⚠️  Les CRASC existent déjà. Arrêt du script.")
                print("💡 Si vous souhaitez réinitialiser, supprimez d'abord les CRASC existants.")
                return

            # Créer les nouveaux CRASC
            created_count = 0
            for crasc_data in CRASC_DATA:
                # Vérifier si le CRASC existe déjà par slug
                result = await db.execute(
                    select(Crasc).where(Crasc.slug == crasc_data["slug"])
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    crasc = Crasc(**crasc_data)
                    db.add(crasc)
                    created_count += 1
                    print(f"✅ CRASC créé: {crasc_data['name']}")
                else:
                    print(f"ℹ️  CRASC déjà existant: {crasc_data['name']}")

            await db.commit()

            print("=" * 60)
            print(f"🎉 Initialisation terminée ! {created_count} CRASC créés.")
            print("=" * 60)

            # Afficher tous les CRASC
            result = await db.execute(select(Crasc))
            all_crasc = result.scalars().all()
            print(f"\n📋 Liste des CRASC ({len(all_crasc)}) :")
            for crasc in all_crasc:
                print(f"   - {crasc.name} (slug: {crasc.slug})")
            print("=" * 60)

        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {str(e)}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(init_crasc())
