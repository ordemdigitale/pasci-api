from typing import Optional


FORMALISATION_POINTS = {
    "statuts_reglement": 1,
    "recepisse_depot": 3,
    "recepisse_declaration": 5,
    "agrement_decret": 5,
    "journal_officiel": 7,
}

COULEUR_HEX = {
    "gris": "#6B7280",
    "rouge": "#DC2626",
    "orange": "#EA580C",
    "jaune": "#CA8A04",
    "bleu": "#2563EB",
    "vert": "#16A34A",
}


def calculer_score_autoevaluation(
    type_document_formalisation: Optional[str],
    existence_siege: Optional[bool],
    manuel_procedures: Optional[bool],
    plan_action: Optional[bool],
    rapports_annuels: Optional[bool],
    adhesion_crasc: Optional[bool],
    adhesion_crasc_statut: Optional[str] = None,
) -> int:
    adhesion_oui = adhesion_crasc_statut == "oui" if adhesion_crasc_statut else bool(adhesion_crasc)
    return min(
        20,
        FORMALISATION_POINTS.get(type_document_formalisation or "", 0)
        + (3 if existence_siege else 0)
        + (3 if manuel_procedures else 0)
        + (3 if plan_action else 0)
        + (3 if rapports_annuels else 0)
        + (1 if adhesion_oui else 0),
    )


def couleur_pour_score(score: int) -> str:
    if score <= 0:
        return "gris"
    if score <= 5:
        return "rouge"
    if score <= 8:
        return "orange"
    if score <= 12:
        return "jaune"
    if score <= 15:
        return "bleu"
    return "vert"
