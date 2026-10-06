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


def expression_score_sql(osc):
    """
    Version SQL de `calculer_score_autoevaluation`, pour filtrer et trier sur
    le score sans charger toutes les OSC en mémoire. Doit rester alignée sur
    la version Python ci-dessus (le maximum atteignable est exactement 20,
    il n'y a donc pas de plafond à appliquer ici).
    """
    from sqlalchemy import and_, case, or_

    formalisation = case(
        *[
            (osc.type_document_formalisation == valeur, points)
            for valeur, points in FORMALISATION_POINTS.items()
        ],
        else_=0,
    )
    critere = lambda colonne: case((colonne == True, 3), else_=0)  # noqa: E712, E731
    # Le statut prime sur le booléen ; sans statut renseigné on retombe dessus.
    adhesion = case(
        (osc.adhesion_crasc_statut == "oui", 1),
        (
            and_(
                or_(osc.adhesion_crasc_statut.is_(None), osc.adhesion_crasc_statut == ""),
                osc.adhesion_crasc == True,  # noqa: E712
            ),
            1,
        ),
        else_=0,
    )
    return (
        formalisation
        + critere(osc.existence_siege)
        + critere(osc.manuel_procedures)
        + critere(osc.plan_action)
        + critere(osc.rapports_annuels)
        + adhesion
    )


# Barème affiché à l'utilisateur (annuaire, profil OSC, back-office).
BAREME = [
    {
        "critere": "Document de formalisation",
        "points": 7,
        "detail": "Journal Officiel 7 · Récépissé de déclaration 5 · Agrément/décret 5 · Récépissé de dépôt 3 · Statuts et règlement intérieur 1",
    },
    {"critere": "Existence d'un siège", "points": 3, "detail": "Siège social identifié"},
    {"critere": "Plan d'action", "points": 3, "detail": "Plan d'action formalisé"},
    {"critere": "Rapports annuels d'activités", "points": 3, "detail": "Rapports d'activités produits"},
    {"critere": "Manuel de procédures", "points": 3, "detail": "Manuel de procédures en vigueur"},
    {"critere": "Adhésion au CRASC", "points": 1, "detail": "Adhésion effective au CRASC"},
]

# Tranches de couleur, alignées sur `couleur_pour_score`.
TRANCHES_COULEUR = [
    {"couleur": "rouge", "min": 1, "max": 5, "libelle": "Très faible"},
    {"couleur": "orange", "min": 6, "max": 8, "libelle": "Faible"},
    {"couleur": "jaune", "min": 9, "max": 12, "libelle": "Moyen"},
    {"couleur": "bleu", "min": 13, "max": 15, "libelle": "Bon"},
    {"couleur": "vert", "min": 16, "max": 20, "libelle": "Très bon"},
]
