# services/recherche.py
"""
Recherche insensible à la casse **et aux accents**.

La base de production n'a pas l'extension `unaccent` (son installation
demande un superutilisateur PostgreSQL) : le repli est `translate()`, une
fonction standard disponible partout, qui remplace caractère par caractère
les lettres accentuées par leur équivalent non accentué.

Sans cela, « société » ne trouve pas « SOCIETE » et « San-Pedro » ne trouve
pas « San-Pédro » : des OSC pourtant enregistrées restaient introuvables.

La casse et les accents ne sont pas les seules sources d'échec : « San Pedro »
doit aussi retrouver « San-Pédro ». La ponctuation est donc ramenée à des
espaces, puis les espaces consécutifs sont fusionnés, des deux côtés de la
comparaison.
"""
import re
import unicodedata
from typing import Optional

from sqlalchemy import func, literal, or_

# Les deux chaînes doivent avoir exactement la même longueur : translate()
# associe le n-ième caractère de l'une au n-ième caractère de l'autre.
_PONCTUATION = "-_'’`´.,;:!?/\\|()[]{}<>\"«»&+*#@~^°%$€"
_ACCENTS = "àáâãäåāăąçćĉċčèéêëēĕėęěìíîïĩīĭįıñńņňòóôõöøōŏőùúûüũūŭůűųýÿŷßÀÁÂÃÄÅĀĂĄÇĆĈĊČÈÉÊËĒĔĖĘĚÌÍÎÏĨĪĬĮİÑŃŅŇÒÓÔÕÖØŌŎŐÙÚÛÜŨŪŬŮŰŲÝŸŶ"
_SANS_ACCENTS = "aaaaaaaaaccccceeeeeeeeeiiiiiiiiinnnnooooooooouuuuuuuuuuyyysAAAAAAAAACCCCCEEEEEEEEEIIIIIIIIINNNNOOOOOOOOOUUUUUUUUUUYYY"

_DEPUIS = _ACCENTS + _PONCTUATION
_VERS = _SANS_ACCENTS + " " * len(_PONCTUATION)

assert len(_ACCENTS) == len(_SANS_ACCENTS), "tables de translittération désalignées"
assert len(_DEPUIS) == len(_VERS), "tables de translittération désalignées"


def normaliser(valeur: Optional[str]) -> str:
    """Minuscules, sans accents ni ponctuation — version Python de `sans_accents()`."""
    texte = unicodedata.normalize("NFD", valeur or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = texte.lower().translate(str.maketrans(_PONCTUATION, " " * len(_PONCTUATION)))
    return re.sub(r"\s+", " ", texte).strip()


def sans_accents(colonne):
    """Expression SQL : la colonne en minuscules, sans accents ni ponctuation."""
    return func.btrim(
        func.regexp_replace(
            func.translate(func.lower(colonne), literal(_DEPUIS), literal(_VERS)),
            literal(r"\s+"),
            literal(" "),
            literal("g"),
        )
    )


def _echapper(terme: str) -> str:
    """Neutralise les jokers LIKE saisis par l'utilisateur."""
    return terme.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contient(colonne, terme: Optional[str]):
    """`colonne` contient `terme`, sans tenir compte de la casse ni des accents."""
    motif = f"%{_echapper(normaliser(terme))}%"
    return sans_accents(colonne).like(motif, escape="\\")


def egal(colonne, terme: Optional[str]):
    """`colonne` égale `terme`, sans tenir compte de la casse ni des accents."""
    return sans_accents(colonne) == normaliser(terme)


def contient_un_de(colonnes, terme: Optional[str]):
    """`terme` apparaît dans au moins une des colonnes."""
    return or_(*[contient(colonne, terme) for colonne in colonnes])
