# services/task_force.py | Référentiels de l'espace Taskforce
"""
Arborescence documentaire de l'espace PdoC des task forces et zones couvertes.

L'arborescence est fixée par le cahier des charges PdoC : elle sert à ranger
les dépôts et à présenter l'espace, côté public comme en back-office.
"""

# Zones des task forces thématiques régionales
ZONES_TASK_FORCE = ["Nord", "Sud", "Est", "Ouest", "Centre"]

# catégorie → sous-catégories (vide = dépôt directement dans la catégorie)
ARBORESCENCE_DOCUMENTS = {
    "Outils de travail": [
        "Plan d'action annuel",
        "Feuille de route de mobilisation des ressources",
    ],
    "Rapports et comptes rendus de travail": [
        "Rapport annuel de capitalisation",
        "Rapport d'études participatives",
        "Rapports trimestriels",
        "Rapport de campagnes numériques",
        "Étude ou diagnostic participatif",
    ],
    "Cartographie de données": [
        "Cartographie des acteurs",
        "Cartographie des problèmes",
        "Cartographie des partenaires",
        "Tableau de suivi des engagements publics",
    ],
    "Notes": [
        "Notes de position",
        "Notes de plaidoyer",
        "Notes techniques",
    ],
}


def categorie_valide(categorie: str) -> bool:
    return categorie in ARBORESCENCE_DOCUMENTS


def sous_categorie_valide(categorie: str, sous_categorie: str | None) -> bool:
    """Une sous-catégorie vide est acceptée : le document est rangé à la racine."""
    if not sous_categorie:
        return True
    return sous_categorie in ARBORESCENCE_DOCUMENTS.get(categorie, [])


def arborescence() -> list[dict]:
    """Arborescence exposée au front, dans l'ordre du cahier des charges."""
    return [
        {"categorie": categorie, "sous_categories": sous_categories}
        for categorie, sous_categories in ARBORESCENCE_DOCUMENTS.items()
    ]
