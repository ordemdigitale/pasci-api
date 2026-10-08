# services/forum_synthese.py
"""
Brouillon de synthèse d'une discussion de pôle, généré automatiquement à partir
des contributions (sans service d'IA externe) : chronologie, participants,
idées exprimées par chacun, mots-clés récurrents. L'administrateur le relit et
le complète avant de publier la synthèse.
"""
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import List, Optional

# Mots trop courants pour être des mots-clés (français)
MOTS_VIDES = set("""
a afin ainsi alors au aucun aussi autre autres aux avec avoir avons bien car ce ceci cela celle celles celui
ces cet cette chaque chez comme comment dans de des donc dont du elle elles en encore entre est et etait
etre eux faire fait faut il ils je la le les leur leurs lui mais me meme mes moi mon ne nos notre nous on ont
ou par pas peu peut plus pour pourquoi quand que quel quelle quelles quels qui sa sans se selon ses si son
sont sur ta tes toi ton tous tout toute toutes tres tu un une vos votre vous ya cest quil jai nest cela doit
doivent etre avez ete sera seront nous vous merci bonjour bonsoir aussi tout avons ainsi entre afin depuis
""".split())


def _sans_accents(texte: str) -> str:
    texte = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def mots_cles(textes: List[str], nombre: int = 10) -> List[str]:
    """Mots les plus fréquents (5 lettres et plus, hors mots vides)."""
    compteur: Counter = Counter()
    forme: dict = {}
    for texte in textes:
        for mot in re.findall(r"[A-Za-zÀ-ÿ'-]{5,}", texte or ""):
            cle = _sans_accents(mot.lower()).strip("'-")
            if len(cle) < 5 or cle in MOTS_VIDES:
                continue
            compteur[cle] += 1
            forme.setdefault(cle, mot.lower())
    return [forme[cle] for cle, n in compteur.most_common(nombre) if n >= 2]


def _premieres_phrases(texte: str, max_car: int = 280) -> str:
    texte = re.sub(r"\s+", " ", texte or "").strip()
    if len(texte) <= max_car:
        return texte
    coupe = texte[:max_car]
    fin = max(coupe.rfind(". "), coupe.rfind("! "), coupe.rfind("? "))
    return (coupe[: fin + 1] if fin > 80 else coupe.rsplit(" ", 1)[0] + "…").strip()


def _date(d: Optional[datetime]) -> str:
    return d.strftime("%d/%m/%Y") if d else "?"


def brouillon(sujet_titre: str, sujet_contenu: str, pole_nom: str, contributions: List[dict]) -> str:
    """
    contributions : [{auteur, osc, date (datetime), contenu, medias (int)}],
    dans l'ordre chronologique.
    """
    lignes = [f"Synthèse de la discussion « {sujet_titre} » — pôle {pole_nom}", ""]
    if not contributions:
        lignes += ["Aucune contribution pour le moment.", "", "Question posée :", _premieres_phrases(sujet_contenu, 600)]
        return "\n".join(lignes)

    participants = {c["auteur"] for c in contributions}
    oscs = {c["osc"] for c in contributions if c.get("osc")}
    medias = sum(c.get("medias", 0) for c in contributions)
    lignes += [
        f"Période : du {_date(contributions[0]['date'])} au {_date(contributions[-1]['date'])}.",
        f"Participation : {len(contributions)} contribution(s) de {len(participants)} participant(s)"
        + (f", représentant {len(oscs)} OSC" if oscs else "")
        + (f" ; {medias} média(s) partagé(s)" if medias else "")
        + ".",
        "",
        "Question posée :",
        _premieres_phrases(sujet_contenu, 600),
        "",
        "Idées exprimées :",
    ]
    for c in contributions:
        qui = c["auteur"] + (f" ({c['osc']})" if c.get("osc") else "")
        extrait = _premieres_phrases(c["contenu"]) or "(contribution sans texte)"
        if c.get("medias"):
            extrait += f" [{c['medias']} média(s) joint(s)]"
        lignes.append(f"- {qui} : {extrait}")

    cles = mots_cles([sujet_contenu] + [c["contenu"] for c in contributions])
    if cles:
        lignes += ["", "Mots-clés récurrents : " + ", ".join(cles) + "."]
    lignes += [
        "",
        "Points de convergence : …",
        "Points de divergence : …",
        "Recommandations / prochaines étapes : …",
    ]
    return "\n".join(lignes)
