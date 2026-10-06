# services/rattachement.py
"""
Rattachement d'une OSC à son pôle de concertation, son type et sa région.

Les pôles de concertation portent le nom des domaines prioritaires
("Santé", "Éducation", ...) : le 1er domaine prioritaire d'une OSC désigne
son pôle. Les noms saisis dans les formulaires diffèrent souvent de ceux en
base par les accents, la casse ou la ponctuation ("Gbôklé" / "Gbôklê",
"San-Pédro" / "San Pedro", "ONG" / "Organisation Non Gouvernementale (ONG)") :
toutes les comparaisons passent donc par `normaliser`.
"""
import re
import unicodedata
from typing import Optional

from sqlalchemy import delete, insert, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.crasc import Osc, OscType, Region, osc_pole_link
from app.models.forum import PoleConcertation

# Préfixes administratifs ignorés dans les noms de région
_PREFIXES_REGION = ("district autonome de ", "district autonome d ", "district d ", "region de ", "region du ")


def normaliser(valeur: Optional[str]) -> str:
    """Minuscules, sans accents, ponctuation remplacée par des espaces."""
    texte = unicodedata.normalize("NFD", valeur or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = re.sub(r"[^a-z0-9]+", " ", texte.lower())
    return texte.strip()


def _cle_region(valeur: Optional[str]) -> str:
    cle = normaliser(valeur)
    for prefixe in _PREFIXES_REGION:
        if cle.startswith(prefixe):
            return cle[len(prefixe):].strip()
    return cle


async def _charger(db: AsyncSession, cle: str, requete):
    """
    Charge une table de référence une seule fois par session : le rattrapage
    traite des centaines d'OSC d'affilée.
    """
    cache = db.sync_session.info.setdefault("rattachement_cache", {})
    if cle not in cache:
        cache[cle] = (await db.execute(requete)).scalars().all()
    return cache[cle]


async def trouver_pole(db: AsyncSession, domaine: Optional[str]) -> Optional[PoleConcertation]:
    """Pôle actif dont le nom correspond au domaine prioritaire."""
    cle = normaliser(domaine)
    if not cle:
        return None
    poles = await _charger(
        db, "poles", select(PoleConcertation).where(PoleConcertation.is_active == True)  # noqa: E712
    )
    for pole in poles:
        if normaliser(pole.name) == cle or normaliser(pole.category) == cle:
            return pole
    return None


async def trouver_type(db: AsyncSession, type_saisi: Optional[str]) -> Optional[OscType]:
    """
    Type d'OSC correspondant au libellé saisi : correspondance exacte, ou
    sigle entre parenthèses ("ONG" -> "Organisation Non Gouvernementale (ONG)").
    """
    cle = normaliser(type_saisi)
    if not cle:
        return None
    types = await _charger(db, "types", select(OscType))
    for osc_type in types:
        if normaliser(osc_type.name) == cle:
            return osc_type
    for osc_type in types:
        sigles = re.findall(r"\(([^)]+)\)", osc_type.name or "")
        if any(normaliser(sigle) == cle for sigle in sigles):
            return osc_type
    return None


async def trouver_region(db: AsyncSession, region_saisie: Optional[str]) -> Optional[Region]:
    cle = _cle_region(region_saisie)
    if not cle:
        return None
    regions = await _charger(db, "regions", select(Region))
    for region in regions:
        if _cle_region(region.name) == cle:
            return region
    return None


def vider_cache(db: AsyncSession) -> None:
    """À appeler après une modification des pôles (fusion, renommage)."""
    db.sync_session.info.pop("rattachement_cache", None)


async def poles_de_osc(db: AsyncSession, osc_id: int) -> list[int]:
    result = await db.execute(
        select(osc_pole_link.c.pole_id).where(osc_pole_link.c.osc_id == osc_id)
    )
    return list(result.scalars().all())


async def definir_pole(db: AsyncSession, osc_id: int, pole_id: int) -> None:
    """Une OSC n'appartient qu'à un seul pôle : remplace ses rattachements."""
    await db.execute(delete(osc_pole_link).where(osc_pole_link.c.osc_id == osc_id))
    await db.execute(insert(osc_pole_link).values(osc_id=osc_id, pole_id=pole_id))


async def rattacher_osc(
    db: AsyncSession,
    osc: Osc,
    type_saisi: Optional[str] = None,
) -> dict:
    """
    Complète ce qui manque à l'OSC : pôle (depuis le 1er domaine prioritaire),
    type, région et CRASC (depuis la région). Ne remplace jamais une valeur
    déjà renseignée. L'OSC doit avoir un id (flush fait). Ne commit pas.

    Retourne ce qui a été rattaché, pour le journal du rattrapage.
    """
    rattache: dict = {}

    if osc.domaine_prioritaire and not await poles_de_osc(db, osc.id):
        pole = await trouver_pole(db, osc.domaine_prioritaire)
        if pole:
            await definir_pole(db, osc.id, pole.id)
            rattache["pole"] = pole.name

    if not osc.type_id and type_saisi:
        osc_type = await trouver_type(db, type_saisi)
        if osc_type:
            osc.type_id = osc_type.id
            rattache["type"] = osc_type.name

    if not osc.region_id and osc.region_nom:
        region = await trouver_region(db, osc.region_nom)
        if region:
            osc.region_id = region.id
            rattache["region"] = region.name
            if not osc.crasc_id and region.crasc_id:
                osc.crasc_id = region.crasc_id
                rattache["crasc_id"] = region.crasc_id

    return rattache
