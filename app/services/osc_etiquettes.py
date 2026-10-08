# services/osc_etiquettes.py
"""
Étiquettes des OSC : OdF, OdJ, OPSH et faîtières.

- OdF / OdJ / OPSH / mixte : valeur du champ `categorie` (question « Catégorie
  d'organisation » du questionnaire). La valeur attendue est le code interne,
  mais d'anciennes fiches portent le libellé complet ou le sigle : toutes ces
  écritures sont reconnues, sans casse ni accents.
- Faîtière : déduite du niveau de regroupement (réseau, fédération,
  plateforme, confédération) : une organisation « simple » n'en est pas une.
"""
from typing import List, Optional

from sqlalchemy import or_

from app.services.recherche import egal, normaliser

# code → (sigle, libellé, écritures reconnues)
CATEGORIES = {
    "organisation_femme": (
        "OdF", "Organisation de femmes",
        ["organisation_femme", "organisation de femme", "organisation de femmes", "organisation des femmes",
         "organisation feminine", "odf"],
    ),
    "organisation_jeune": (
        "OdJ", "Organisation de jeunes",
        ["organisation_jeune", "organisation de jeune", "organisation de jeunes", "organisation des jeunes",
         "organisation de jeunesse", "odj"],
    ),
    "organisation_handicap": (
        "OPSH", "Organisation de personnes en situation de handicap",
        ["organisation_handicap", "organisation de personnes en situation de handicap",
         "organisation de personnes handicapees", "organisation des personnes handicapees",
         "organisation de personnes vivant avec un handicap", "opsh"],
    ),
    "organisation_mixte": (
        None, "Organisation mixte",
        ["organisation_mixte", "organisation mixte", "mixte"],
    ),
}

CATEGORIE_SYNONYMES = {code: ecritures for code, (_, _, ecritures) in CATEGORIES.items()}

# Niveaux de regroupement qui font d'une organisation une faîtière
NIVEAUX_FAITIERE = ("reseau", "federation", "plateforme", "confederation")
TERMES_FAITIERE = ("faitiere", "faitieres", "organisation faitiere")


def code_categorie(valeur: Optional[str]) -> Optional[str]:
    """Code interne d'une catégorie, quelle que soit son écriture (None si inconnue)."""
    terme = normaliser(valeur)
    if not terme:
        return None
    for code, ecritures in CATEGORIE_SYNONYMES.items():
        if terme in (normaliser(e) for e in ecritures):
            return code
    return None


def est_faitiere(niveau_regroupement: Optional[str]) -> bool:
    return normaliser(niveau_regroupement) in NIVEAUX_FAITIERE


def etiquettes(categorie: Optional[str], niveau_regroupement: Optional[str]) -> List[str]:
    """Sigles affichés sur la fiche : OdF, OdJ, OPSH et/ou Faîtière."""
    resultat = []
    code = code_categorie(categorie)
    if code and CATEGORIES[code][0]:
        resultat.append(CATEGORIES[code][0])
    if est_faitiere(niveau_regroupement):
        resultat.append("Faîtière")
    return resultat


def filtre_categorie(colonne, valeur: str):
    """Accepte le code interne, le libellé complet ou le sigle (OdJ, OdF, OPSH)."""
    code = code_categorie(valeur) or valeur
    ecritures = CATEGORIE_SYNONYMES.get(code, [valeur])
    return or_(*[egal(colonne, ecriture) for ecriture in ecritures])


def filtre_faitiere(colonne):
    return or_(*[egal(colonne, niveau) for niveau in NIVEAUX_FAITIERE])
