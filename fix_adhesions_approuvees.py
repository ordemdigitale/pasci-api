"""
Script de rattrapage : rendre visibles les OSC issues de demandes d'adhésion
déjà approuvées.

Contexte (deux bugs corrigés dans app/api/v1/endpoints/adhesion.py) :

  1. L'OSC était créée avec statut_publication="en_attente" alors que les
     listes/annuaires ne renvoient que statut_publication="publie".
     → OSC créée mais invisible, coincée dans /admin/moderation.

  2. Pour un approbateur is_staff non-superuser (admin CRASC), la ligne
     `demande.crasc_id_override = ...` levait une ValueError avalée par un
     `except` silencieux.
     → demande marquée "approuvee" mais NI OSC NI compte utilisateur créés.

Ce script traite les deux cas sur les données existantes :

  - Cas 1 : OSC dont le nom correspond à une demande approuvée et qui est
            encore en "en_attente"  →  passée à "publie".
  - Cas 2 : demande approuvée sans OSC correspondante  →  OSC + compte
            utilisateur (re)créés via la même fonction que l'API.

  - Option --tout : publie AUSSI les OSC restées en "en_attente" qui ne
            viennent pas d'une demande (créées à la main via l'admin), la
            modération des nouvelles OSC ayant été supprimée. Les OSC
            explicitement "rejete" ne sont jamais touchées.

Usage :
    python fix_adhesions_approuvees.py                # dry-run (n'écrit rien)
    python fix_adhesions_approuvees.py --apply        # applique les changements
    python fix_adhesions_approuvees.py --apply --tout # + vide la file de modération OSC
    python fix_adhesions_approuvees.py --apply --credentials creds.csv
                                                      # + export des identifiants créés
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

import importlib  # noqa: E402
import pkgutil  # noqa: E402

from sqlalchemy import func  # noqa: E402
from sqlmodel import select  # noqa: E402

import app.models as _models_pkg  # noqa: E402

# Charger TOUS les modèles : sans ça, SQLAlchemy échoue à configurer les
# mappers (relations 'Formation', 'News'… non résolues) au premier select.
for _module in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_module.name}")

from app.database.session import AsyncSessionLocal  # noqa: E402
from app.models.adhesion import DemandeAdhesion  # noqa: E402
from app.models.crasc import Osc  # noqa: E402
from app.api.v1.endpoints.adhesion import _normaliser_nom, _provision_osc_and_user  # noqa: E402


async def run(apply: bool, credentials_path: str | None, tout: bool) -> int:
    published: list[str] = []
    published_hors_demande: list[str] = []
    provisioned: list[tuple[str, str, str, str]] = []
    failed: list[tuple[str, str]] = []
    already_ok = 0

    async with AsyncSessionLocal() as db:
        demandes = (
            await db.execute(
                select(DemandeAdhesion)
                .where(DemandeAdhesion.statut == "approuvee")
                .order_by(DemandeAdhesion.created_at)
            )
        ).scalars().all()

        print(f"Demandes approuvées : {len(demandes)}\n")

        for demande in demandes:
            # Comparaison normalisée, identique à celle du provisionnement
            osc = (
                await db.execute(
                    select(Osc)
                    .where(func.lower(func.btrim(Osc.name)) == _normaliser_nom(demande.nom_organisation))
                    .order_by(Osc.id)
                )
            ).scalars().first()

            # ── Cas 2 : aucune OSC → (re)provisionner ────────────────────────
            if not osc:
                if not apply:
                    print(f"[MANQUANTE]  {demande.nom_organisation}  (demande #{demande.id})")
                    provisioned.append((demande.nom_organisation, "", "", ""))
                    continue
                try:
                    creds = await _provision_osc_and_user(demande, db)
                    print(f"[CRÉÉE]      {creds.osc_name}  → user {creds.username}")
                    provisioned.append(
                        (creds.osc_name, creds.email, creds.username, creds.temp_password)
                    )
                except Exception as exc:  # noqa: BLE001
                    await db.rollback()
                    print(f"[ÉCHEC]      {demande.nom_organisation} : {exc}", file=sys.stderr)
                    failed.append((demande.nom_organisation, str(exc)))
                continue

            # ── Cas 1 : OSC existante mais pas publiée ───────────────────────
            if osc.statut_publication == "publie":
                already_ok += 1
                continue

            if osc.statut_publication == "rejete":
                # Rejet explicite par un admin : on n'y touche pas.
                print(f"[IGNORÉE]    {osc.name}  (statut_publication=rejete)")
                continue

            print(f"[À PUBLIER]  {osc.name}  ({osc.statut_publication} → publie)")
            published.append(osc.name)
            if apply:
                osc.statut_publication = "publie"

        # ── Option --tout : vider la file de modération des nouvelles OSC ────
        if tout:
            noms_demandes = {_normaliser_nom(d.nom_organisation) for d in demandes}
            restantes = (
                await db.execute(
                    select(Osc)
                    .where(Osc.statut_publication == "en_attente")
                    .order_by(Osc.created_at)
                )
            ).scalars().all()
            for osc in restantes:
                if _normaliser_nom(osc.name) in noms_demandes:
                    continue  # déjà traité au-dessus
                print(f"[À PUBLIER*] {osc.name}  (créée hors demande d'adhésion)")
                published_hors_demande.append(osc.name)
                if apply:
                    osc.statut_publication = "publie"

        if apply:
            await db.commit()

    print("\n" + "─" * 70)
    print(f"Déjà publiées (rien à faire) : {already_ok}")
    print(f"OSC passées à 'publie'       : {len(published)}")
    print(f"OSC créées (cas 2)           : {len(provisioned)}")
    if tout:
        print(f"OSC publiées hors demande    : {len(published_hors_demande)}")
    if failed:
        print(f"Échecs                       : {len(failed)}")
        for name, err in failed:
            print(f"   - {name} : {err}")
    if not apply:
        print("\n⚠️  DRY-RUN : aucune écriture en base. Relancer avec --apply.")

    if apply and credentials_path and provisioned:
        with open(credentials_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["osc_name", "email", "username", "temp_password"])
            writer.writerows(provisioned)
        print(f"\nIdentifiants créés exportés dans {credentials_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Applique les changements en base")
    parser.add_argument("--credentials", default=None, help="Fichier CSV d'export des identifiants créés")
    parser.add_argument(
        "--tout",
        action="store_true",
        help="Publie aussi les OSC en_attente créées hors demande d'adhésion",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.apply, args.credentials, args.tout)))
