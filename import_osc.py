"""
Script d'import des OSC depuis le fichier Excel "Base OSCI 2026.xlsx"
vers la base de données PostgreSQL du projet PASCI.

Usage:
    python import_osc.py [--dry-run] [--excel /chemin/vers/fichier.xlsx]

Options:
    --dry-run   Simule l'import sans rien écrire en base
    --excel     Chemin vers le fichier Excel (défaut: Base OSCI 2026.xlsx)
"""

import asyncio
import argparse
import sys
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Chargement du .env
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

import openpyxl
import slugify as slugify_lib
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ─── Configuration ────────────────────────────────────────────────────────────

EXCEL_DEFAULT = Path(__file__).parent.parent / "Base OSCI 2026.xlsx"

# Index 0-based des colonnes clés dans la feuille principale
COL = {
    "zone":     14,   # Zone CRASC (Sud, Nord, Est, Ouest, Centre)
    "region_s": 15,   # Région Sud
    "region_n": 54,   # Région Nord
    "region_e": 84,   # Région Est
    "region_c": 108,  # Région Centre
    "region_o": 134,  # Région Ouest
    "nom":      160,  # Nom complet de l'organisation
    "sigle":    161,  # Sigle/acronyme
    "ville":    166,  # Situation géographique / ville
    "tel":      167,  # Contact téléphonique fixe
    "mobile":   168,  # Contact cellulaire
    "email":              171,  # Email
    "type":               181,  # Type d'organisation
    "mission":            236,  # Missions de l'OSC
    "lat":                3,    # Latitude GPS
    "lon":                4,    # Longitude GPS
    "website":            170,  # Site web
    "reseaux_sociaux":    172,  # Réseaux sociaux
    "date_creation":      173,  # Date de création
    "numero_recepisse":   177,  # N° récépissé
    "niveau_couverture":  182,  # Niveau de couverture
    "zone_couverture":    183,  # Zone de couverture
    "categorie":          198,  # Catégorie d'organisation
    "domaine_prioritaire":   231, # 1er domaine prioritaire
    "domaine_prioritaire_2": 232, # 2ème domaine prioritaire
    "domaine_prioritaire_3": 233, # 3ème domaine prioritaire
    "domaine_prioritaire_4": 234, # 4ème domaine prioritaire
    "nb_membres":            267, # Nombre total de membres
    "nb_femmes_membres":     269, # Nombre de femmes membres
    "nb_membres_jeunes":     270, # Nombre de membres jeunes
    "nb_membres_be":         272, # Nombre de membres du bureau exécutif
    "nb_personnes_engagees": 273, # Nombre de personnes engagées
    "nb_beneficiaires":      254, # Nombre de bénéficiaires
    "nb_activites":          295, # Nombre d'activités
    "budget_annuel":         302, # Budget annuel en F/CFA
    "type_financement":      303, # Type de financement (texte)
    "montant_cotisation":    316, # Montant de la cotisation
    "etat_cotisations":      317, # État des cotisations
    "sexe_president":        285, # Sexe du président
    "mode_designation_president": 286, # Mode de désignation
    "duree_mandat_be":       283, # Durée mandat bureau exécutif
    "adhesion_crasc":        258, # Adhésion au CRASC (boolean)
    "reseau_appartenance":   210, # Réseau d'appartenance
    "secteurs_activites":    212, # Secteurs d'activités
    "populations_cibles":    237, # Populations cibles
    "savoir_faire":          320, # Savoir-faire
    "difficultes":           321, # Difficultés rencontrées
    "recommandations":       322, # Recommandations
    # Sources de financement (colonnes booléennes)
    "fin_cotisation":        306,
    "fin_dons":              307,
    "fin_legs":              308,
    "fin_collectivites":     309,
    "fin_fonds_propres":     310,
    "fin_ong_intl":          311,
    "fin_multilateral":      312,
}

# Correspondance Zone Excel → nom CRASC attendu en base
ZONE_MAP = {
    "Sud":    "CRASC Sud",
    "Nord":   "CRASC Nord",
    "Est":    "CRASC Est",
    "Ouest":  "CRASC Ouest",
    "Centre": "CRASC Centre",
}

# Correspondance Type Excel → nom OscType attendu en base
TYPE_MAP = {
    "Association":                               "Association",
    "Fondation":                                 "Fondation",
    "Organisation Non Gouvernementale (ONG)":    "Organisation Non Gouvernementale (ONG)",
    "Organisation cultuelle":                    "Organisation cultuelle",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean_str(val) -> str:
    """Nettoie une valeur texte."""
    if val is None:
        return None
    s = str(val).strip()
    # Supprimer les caractères de contrôle
    s = re.sub(r'[\x00-\x1f\x7f]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s or None


def clean_phone(val) -> str:
    """Convertit un numéro de téléphone en chaîne propre."""
    if val is None:
        return None
    s = re.sub(r'[^\d+]', '', str(val))
    return s or None


def clean_float(val) -> float:
    """Convertit une valeur en float."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


def clean_int(val) -> int:
    """Convertit une valeur en int."""
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def clean_url(val) -> str:
    """Nettoie une URL — ignore les valeurs '0' ou trop courtes."""
    s = clean_str(val)
    if not s or s == '0' or not s.startswith('http'):
        return None
    return s[:500]


def clean_date(val) -> str:
    """Extrait la date (YYYY-MM-DD) depuis une valeur datetime."""
    if val is None:
        return None
    s = str(val).strip()
    # Format: "2024-01-07 00:00:00" → "2024-01-07"
    if len(s) >= 10 and s[4] == '-':
        return s[:10]
    return s[:30] or None


def clean_bool(val) -> bool:
    """Convertit une valeur en booléen : '1', 1, 'oui', 'yes', 'true' → True."""
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ('1', 'oui', 'yes', 'true', 'vrai'):
        return True
    if s in ('0', 'non', 'no', 'false', 'faux', ''):
        return False
    return None


def get_region(row) -> str:
    """Extrait la région depuis les colonnes de régions (une seule est remplie)."""
    for col_key in ("region_s", "region_n", "region_e", "region_c", "region_o"):
        val = clean_str(row[COL[col_key]])
        if val:
            return val
    return None


def make_unique_name(name, zone, used):
    """
    Rend un nom unique en ajoutant la zone ou un suffixe numérique.
    Ex: "ONG ADDY" → "ONG ADDY (Nord)" → "ONG ADDY (Nord) 2"
    """
    candidate = name
    if candidate.upper() in used:
        candidate = f"{name} ({zone})" if zone else name
    if candidate.upper() in used:
        n = 2
        while f"{candidate} {n}".upper() in used:
            n += 1
        candidate = f"{candidate} {n}"
    return candidate


# ─── Import principal ─────────────────────────────────────────────────────────

async def run_import(excel_path: Path, dry_run: bool):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Import OSC depuis : {excel_path}\n")

    # ── Lecture Excel ──────────────────────────────────────────────────────────
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    ws = wb["Plateforme digitale des OSC ..."]
    rows = list(ws.iter_rows(values_only=True))
    data_rows = rows[1:]  # Ignorer l'en-tête
    print(f"✅ Fichier chargé : {len(data_rows)} lignes")

    # ── Connexion DB ───────────────────────────────────────────────────────────
    db_url = settings.ASYNC_DATABASE_URL
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── Charger CRASC existants ────────────────────────────────────────────
        crasc_result = await session.execute(text("SELECT id, name FROM crasc"))
        crasc_db = {row.name: row.id for row in crasc_result}
        print(f"CRASC en base : {list(crasc_db.keys())}")

        # Créer les CRASC manquants
        for zone_label, crasc_name in ZONE_MAP.items():
            if crasc_name not in crasc_db:
                if not dry_run:
                    slug = slugify_lib.slugify(crasc_name)
                    await session.execute(
                        text("INSERT INTO crasc (name, slug, osc_count) VALUES (:n, :s, 0) ON CONFLICT DO NOTHING"),
                        {"n": crasc_name, "s": slug}
                    )
                    await session.commit()
                    result = await session.execute(text("SELECT id FROM crasc WHERE name = :n"), {"n": crasc_name})
                    crasc_db[crasc_name] = result.scalar()
                    print(f"  ➕ CRASC créé : {crasc_name}")
                else:
                    crasc_db[crasc_name] = -1
                    print(f"  [DRY] CRASC à créer : {crasc_name}")

        # ── Charger OscType existants ──────────────────────────────────────────
        type_result = await session.execute(text("SELECT id, name FROM osctype"))
        type_db = {row.name: row.id for row in type_result}
        print(f"Types en base : {list(type_db.keys())}")

        # Créer les types manquants
        for type_name in TYPE_MAP.values():
            if type_name not in type_db:
                if not dry_run:
                    slug = slugify_lib.slugify(type_name)
                    await session.execute(
                        text("INSERT INTO osctype (name, slug) VALUES (:n, :s) ON CONFLICT DO NOTHING"),
                        {"n": type_name, "s": slug}
                    )
                    await session.commit()
                    result = await session.execute(text("SELECT id FROM osctype WHERE name = :n"), {"n": type_name})
                    type_db[type_name] = result.scalar()
                    print(f"  ➕ Type créé : {type_name}")
                else:
                    type_db[type_name] = -1
                    print(f"  [DRY] Type à créer : {type_name}")

        # ── Charger régions existantes ─────────────────────────────────────────
        region_result = await session.execute(text("SELECT id, name FROM region"))
        region_db = {row.name: row.id for row in region_result}
        print(f"Régions en base : {len(region_db)}")

        # ── Charger noms OSC déjà en base (éviter doublons) ───────────────────
        existing_result = await session.execute(text("SELECT UPPER(name) FROM osc"))
        existing_names = {row[0] for row in existing_result}
        print(f"OSC déjà en base : {len(existing_names)}")

        # ── Traitement des lignes ──────────────────────────────────────────────
        used_names = set(existing_names)
        stats = {"insere": 0, "doublon_skip": 0, "sans_nom": 0, "erreur": 0}

        for i, row in enumerate(data_rows, start=2):
            nom = clean_str(row[COL["nom"]])
            if not nom:
                stats["sans_nom"] += 1
                continue

            zone_label = clean_str(row[COL["zone"]])
            crasc_name = ZONE_MAP.get(zone_label)
            crasc_id   = crasc_db.get(crasc_name) if crasc_name else None

            type_label = clean_str(row[COL["type"]])
            type_name  = TYPE_MAP.get(type_label)
            type_id    = type_db.get(type_name) if type_name else None

            # Ignorer si le nom (normalisé) a déjà été traité dans ce run ou en base
            if nom.upper() in used_names:
                stats["doublon_skip"] += 1
                continue
            nom_unique = nom

            # Collecter les champs
            sigle   = clean_str(row[COL["sigle"]])
            ville   = (clean_str(row[COL["ville"]]) or "")[:200] or None
            tel     = clean_phone(row[COL["tel"]]) or clean_phone(row[COL["mobile"]])
            email   = clean_str(row[COL["email"]])
            mission = clean_str(row[COL["mission"]])
            lat     = clean_float(row[COL["lat"]])
            lon     = clean_float(row[COL["lon"]])
            region_name       = get_region(row)
            website           = clean_url(row[COL["website"]])
            reseaux_sociaux   = clean_str(row[COL["reseaux_sociaux"]])
            date_creation     = clean_date(row[COL["date_creation"]])
            numero_recepisse  = clean_str(row[COL["numero_recepisse"]])
            niveau_couverture = clean_str(row[COL["niveau_couverture"]])
            zone_couverture   = clean_str(row[COL["zone_couverture"]])
            categorie         = clean_str(row[COL["categorie"]])
            domaine_prioritaire   = clean_str(row[COL["domaine_prioritaire"]])
            domaine_prioritaire_2 = clean_str(row[COL["domaine_prioritaire_2"]])
            domaine_prioritaire_3 = clean_str(row[COL["domaine_prioritaire_3"]])
            domaine_prioritaire_4 = clean_str(row[COL["domaine_prioritaire_4"]])
            nb_membres            = clean_int(row[COL["nb_membres"]])
            nb_femmes_membres     = clean_int(row[COL["nb_femmes_membres"]])
            nb_membres_jeunes     = clean_int(row[COL["nb_membres_jeunes"]])
            nb_membres_be         = clean_int(row[COL["nb_membres_be"]])
            nb_personnes_engagees = clean_int(row[COL["nb_personnes_engagees"]])
            nb_beneficiaires      = clean_int(row[COL["nb_beneficiaires"]])
            nb_activites          = clean_int(row[COL["nb_activites"]])
            budget_annuel         = clean_int(row[COL["budget_annuel"]])
            type_financement      = clean_str(row[COL["type_financement"]])
            montant_cotisation    = clean_int(row[COL["montant_cotisation"]])
            etat_cotisations      = clean_str(row[COL["etat_cotisations"]])
            sexe_president        = clean_str(row[COL["sexe_president"]])
            mode_designation_president = clean_str(row[COL["mode_designation_president"]])
            duree_mandat_be       = clean_str(row[COL["duree_mandat_be"]])
            adhesion_crasc        = clean_bool(row[COL["adhesion_crasc"]])
            reseau_appartenance   = clean_str(row[COL["reseau_appartenance"]])
            secteurs_activites    = clean_str(row[COL["secteurs_activites"]])
            populations_cibles    = clean_str(row[COL["populations_cibles"]])
            savoir_faire          = clean_str(row[COL["savoir_faire"]])
            difficultes           = clean_str(row[COL["difficultes"]])
            recommandations       = clean_str(row[COL["recommandations"]])
            financement_cotisation    = clean_bool(row[COL["fin_cotisation"]])
            financement_dons          = clean_bool(row[COL["fin_dons"]])
            financement_legs          = clean_bool(row[COL["fin_legs"]])
            financement_collectivites = clean_bool(row[COL["fin_collectivites"]])
            financement_fonds_propres = clean_bool(row[COL["fin_fonds_propres"]])
            financement_ong_intl      = clean_bool(row[COL["fin_ong_intl"]])
            financement_multilateral  = clean_bool(row[COL["fin_multilateral"]])

            # Créer la région si elle n'existe pas encore
            region_id = None
            if region_name:
                if region_name not in region_db:
                    if not dry_run:
                        slug = slugify_lib.slugify(region_name)
                        await session.execute(
                            text("INSERT INTO region (name, slug, crasc_id) VALUES (:n, :s, :c) ON CONFLICT DO NOTHING"),
                            {"n": region_name, "s": slug, "c": crasc_id}
                        )
                        await session.commit()
                        result = await session.execute(text("SELECT id FROM region WHERE name = :n"), {"n": region_name})
                        region_db[region_name] = result.scalar()
                    else:
                        region_db[region_name] = -1
                region_id = region_db.get(region_name)

            # Description = mission + sigle si disponibles
            description_parts = []
            if mission:
                description_parts.append(mission)
            if sigle:
                description_parts.append(f"Sigle : {sigle}")
            description = " | ".join(description_parts) or None
            if description and len(description) > 500:
                description = description[:497] + "..."

            slug = slugify_lib.slugify(nom_unique)[:95]
            # Unicité du slug
            base_slug = slug
            n = 1
            while True:
                check = await session.execute(text("SELECT 1 FROM osc WHERE slug = :s"), {"s": slug})
                if not check.scalar():
                    break
                n += 1
                slug = f"{base_slug}-{n}"

            if not dry_run:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO osc (
                                name, slug, description, type_id, crasc_id, region_id,
                                latitude, longitude, address, email, phone, ville,
                                website, reseaux_sociaux, date_creation, numero_recepisse,
                                niveau_couverture, zone_couverture, categorie,
                                domaine_prioritaire, domaine_prioritaire_2, domaine_prioritaire_3, domaine_prioritaire_4,
                                nb_membres, nb_femmes_membres, nb_membres_jeunes, nb_membres_be,
                                nb_personnes_engagees, nb_beneficiaires, nb_activites,
                                budget_annuel, type_financement, montant_cotisation, etat_cotisations,
                                sexe_president, mode_designation_president, duree_mandat_be, adhesion_crasc,
                                reseau_appartenance, secteurs_activites, populations_cibles,
                                savoir_faire, difficultes, recommandations,
                                financement_cotisation, financement_dons, financement_legs,
                                financement_collectivites, financement_fonds_propres,
                                financement_ong_intl, financement_multilateral
                            ) VALUES (
                                :name, :slug, :desc, :type_id, :crasc_id, :region_id,
                                :lat, :lon, :addr, :email, :phone, :ville,
                                :website, :reseaux_sociaux, :date_creation, :numero_recepisse,
                                :niveau_couverture, :zone_couverture, :categorie,
                                :domaine_prioritaire, :domaine_prioritaire_2, :domaine_prioritaire_3, :domaine_prioritaire_4,
                                :nb_membres, :nb_femmes_membres, :nb_membres_jeunes, :nb_membres_be,
                                :nb_personnes_engagees, :nb_beneficiaires, :nb_activites,
                                :budget_annuel, :type_financement, :montant_cotisation, :etat_cotisations,
                                :sexe_president, :mode_designation_president, :duree_mandat_be, :adhesion_crasc,
                                :reseau_appartenance, :secteurs_activites, :populations_cibles,
                                :savoir_faire, :difficultes, :recommandations,
                                :financement_cotisation, :financement_dons, :financement_legs,
                                :financement_collectivites, :financement_fonds_propres,
                                :financement_ong_intl, :financement_multilateral
                            )
                        """),
                        {
                            "name":               nom_unique,
                            "slug":               slug,
                            "desc":               description,
                            "type_id":            type_id,
                            "crasc_id":           crasc_id,
                            "region_id":          region_id,
                            "lat":                lat,
                            "lon":                lon,
                            "addr":               ville,
                            "email":              email,
                            "phone":              tel,
                            "ville":              ville,
                            "website":            website,
                            "reseaux_sociaux":    reseaux_sociaux,
                            "date_creation":      date_creation,
                            "numero_recepisse":   numero_recepisse,
                            "niveau_couverture":  niveau_couverture,
                            "zone_couverture":    zone_couverture,
                            "categorie":          categorie,
                            "domaine_prioritaire":   domaine_prioritaire,
                            "domaine_prioritaire_2": domaine_prioritaire_2,
                            "domaine_prioritaire_3": domaine_prioritaire_3,
                            "domaine_prioritaire_4": domaine_prioritaire_4,
                            "nb_membres":            nb_membres,
                            "nb_femmes_membres":     nb_femmes_membres,
                            "nb_membres_jeunes":     nb_membres_jeunes,
                            "nb_membres_be":         nb_membres_be,
                            "nb_personnes_engagees": nb_personnes_engagees,
                            "nb_beneficiaires":      nb_beneficiaires,
                            "nb_activites":          nb_activites,
                            "budget_annuel":         budget_annuel,
                            "type_financement":      type_financement,
                            "montant_cotisation":    montant_cotisation,
                            "etat_cotisations":      etat_cotisations,
                            "sexe_president":        sexe_president,
                            "mode_designation_president": mode_designation_president,
                            "duree_mandat_be":       duree_mandat_be,
                            "adhesion_crasc":        adhesion_crasc,
                            "reseau_appartenance":   reseau_appartenance,
                            "secteurs_activites":    secteurs_activites,
                            "populations_cibles":    populations_cibles,
                            "savoir_faire":          savoir_faire,
                            "difficultes":           difficultes,
                            "recommandations":       recommandations,
                            "financement_cotisation":    financement_cotisation,
                            "financement_dons":          financement_dons,
                            "financement_legs":          financement_legs,
                            "financement_collectivites": financement_collectivites,
                            "financement_fonds_propres": financement_fonds_propres,
                            "financement_ong_intl":      financement_ong_intl,
                            "financement_multilateral":  financement_multilateral,
                        }
                    )
                    await session.commit()
                    stats["insere"] += 1
                    used_names.add(nom.upper())
                except Exception as e:
                    await session.rollback()
                    stats["erreur"] += 1
                    print(f"  ❌ Ligne {i} ({nom_unique[:50]}): {e}")
            else:
                stats["insere"] += 1
                used_names.add(nom.upper())

            if stats["insere"] % 100 == 0 and stats["insere"] > 0:
                print(f"  ... {stats['insere']} OSC {'simulés' if dry_run else 'insérés'}")

        # ── Mise à jour osc_count dans chaque CRASC ───────────────────────────
        if not dry_run:
            await session.execute(text("""
                UPDATE crasc c
                SET osc_count = (SELECT COUNT(*) FROM osc WHERE crasc_id = c.id)
            """))
            await session.commit()

    # ── Résumé ────────────────────────────────────────────────────────────────
    print(f"""
{'='*50}
RÉSUMÉ {'(DRY RUN)' if dry_run else ''}
{'='*50}
  ✅ OSC insérés       : {stats['insere']}
  ⏭  Doublons ignorés  : {stats['doublon_skip']}
  ⚠️  Sans nom         : {stats['sans_nom']}
  ❌ Erreurs           : {stats['erreur']}
  TOTAL traité         : {sum(stats.values())}
{'='*50}
""")


# ─── Entrée ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import OSC depuis Excel vers PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans écrire en base")
    parser.add_argument("--excel", type=Path, default=EXCEL_DEFAULT, help="Chemin du fichier Excel")
    args = parser.parse_args()

    if not args.excel.exists():
        print(f"❌ Fichier introuvable : {args.excel}")
        sys.exit(1)

    asyncio.run(run_import(args.excel, args.dry_run))
