#!/usr/bin/env python3
"""
Script pour initialiser les CRASC dans la base de données
"""
import asyncio
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.crasc import Crasc

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


def init_crasc():
    """Initialise les CRASC dans la base de données"""
    db: Session = SessionLocal()

    try:
        print("=€ Initialisation des CRASC...")

        # Vérifier si des CRASC existent déjà
        existing_crasc = db.query(Crasc).all()
        if existing_crasc:
            print(f"   {len(existing_crasc)} CRASC trouvés dans la base de données.")
            response = input("Voulez-vous les supprimer et réinitialiser ? (o/n): ")
            if response.lower() == 'o':
                for crasc in existing_crasc:
                    db.delete(crasc)
                db.commit()
                print(" CRASC existants supprimés")
            else:
                print("L Initialisation annulée")
                return

        # Créer les nouveaux CRASC
        created_count = 0
        for crasc_data in CRASC_DATA:
            # Vérifier si le CRASC existe déjà par slug
            existing = db.query(Crasc).filter(Crasc.slug == crasc_data["slug"]).first()

            if not existing:
                crasc = Crasc(**crasc_data)
                db.add(crasc)
                created_count += 1
                print(f" CRASC créé: {crasc_data['name']}")
            else:
                print(f"í  CRASC déjà existant: {crasc_data['name']}")

        db.commit()
        print(f"\n<‰ Initialisation terminée ! {created_count} CRASC créés.")

        # Afficher tous les CRASC
        all_crasc = db.query(Crasc).all()
        print(f"\n=Ë Liste des CRASC ({len(all_crasc)}) :")
        for crasc in all_crasc:
            print(f"   - {crasc.name} (slug: {crasc.slug})")

    except Exception as e:
        print(f"L Erreur lors de l'initialisation: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_crasc()
