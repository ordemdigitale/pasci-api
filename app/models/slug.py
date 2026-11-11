# models/slug.py | Génération de slug bornée à la taille de la colonne
import slugify


# Marge laissée pour les suffixes d'unicité ajoutés par les endpoints
# (« -1 », « -2 »… quand deux noms produisent le même slug).
MARGE_UNICITE = 5


def generer_slug(valeur: str, taille_colonne: int = 100) -> str:
    """Slug tronqué à la taille de la colonne.

    Les slugs étaient générés sur la longueur entière du nom : un nom
    d'organisation long produisait un slug dépassant varchar(100) et
    l'enregistrement échouait (retour PdoC sur l'inscription des OSC).
    """
    return slugify.slugify(valeur or "")[: max(1, taille_colonne - MARGE_UNICITE)]
