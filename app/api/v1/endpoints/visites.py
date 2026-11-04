import hashlib
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Request
import re
from sqlalchemy import String, cast
from sqlalchemy.exc import IntegrityError
from sqlmodel import select, func, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.database.session import get_db
from app.models.visite import Visite

visites_router = APIRouter()


def _hash_ip(ip: str) -> str:
    """Hash l'IP pour ne stocker aucune donnée personnelle."""
    return hashlib.sha256(ip.encode()).hexdigest()[:32]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Une connexion = l'identifiant envoyé par le navigateur, sinon IP + jour
# (anciennes visites, clients qui ne l'envoient pas)
CONNEXION = func.coalesce(
    Visite.session_id,
    func.concat(Visite.ip_hash, ":", cast(Visite.date_visite, String)),
)


def _nb_connexions(*conditions):
    return select(func.count(func.distinct(CONNEXION))).where(*conditions)


@visites_router.post("", status_code=204)
async def enregistrer_visite(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Enregistre une visite de page.
    Body JSON attendu : { "path": "/formations", "connexion": "<identifiant anonyme>" }
    Déduplication : une page comptée une fois par connexion (retours PdoC :
    « comptabiliser les connexions et non les IP » : plusieurs personnes
    derrière la même IP, un bureau par exemple, comptent séparément).
    Sans identifiant de connexion : 1 visite max par IP + path + jour.
    """
    try:
        body = await request.json()
        path = str(body.get("path", "/"))[:500]
        connexion = str(body.get("connexion") or "")
    except Exception:
        path, connexion = "/", ""
    session_id = connexion if re.fullmatch(r"[A-Za-z0-9-]{8,64}", connexion) else None

    ip = _get_client_ip(request)
    ip_hash = _hash_ip(ip)
    today = date.today()

    deja = select(Visite).where(Visite.path == path)
    if session_id:
        deja = deja.where(Visite.session_id == session_id)
    else:
        deja = deja.where(Visite.ip_hash == ip_hash, Visite.date_visite == today, Visite.session_id.is_(None))
    if (await db.execute(deja)).scalars().first():
        return  # Déjà compté

    visite = Visite(path=path, ip_hash=ip_hash, date_visite=today, session_id=session_id)
    db.add(visite)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # même connexion et même page enregistrées à l'instant par un autre appel


@visites_router.get("/stats")
async def get_stats_visites(db: AsyncSession = Depends(get_db)):
    """Retourne les statistiques de visites pour le dashboard admin."""
    today = date.today()
    hier = today - timedelta(days=1)
    debut_semaine = today - timedelta(days=6)
    debut_mois = today - timedelta(days=29)

    # Connexions (et non plus visiteurs par IP) sur chaque période
    total = (await db.execute(_nb_connexions())).scalar_one()
    pages_vues = (await db.execute(select(func.count(Visite.id)))).scalar_one()
    visiteurs_uniques = (await db.execute(
        select(func.count(func.distinct(Visite.ip_hash)))
    )).scalar_one()
    today_count = (await db.execute(_nb_connexions(Visite.date_visite == today))).scalar_one()
    hier_count = (await db.execute(_nb_connexions(Visite.date_visite == hier))).scalar_one()
    semaine_count = (await db.execute(_nb_connexions(Visite.date_visite >= debut_semaine))).scalar_one()
    mois_count = (await db.execute(_nb_connexions(Visite.date_visite >= debut_mois))).scalar_one()

    # Pages les plus visitées (30 jours)
    top_pages_result = await db.execute(
        select(Visite.path, func.count(Visite.id).label("nb"))
        .where(Visite.date_visite >= debut_mois)
        .group_by(Visite.path)
        .order_by(desc("nb"))
        .limit(5)
    )
    top_pages = [{"path": r.path, "visites": r.nb} for r in top_pages_result.all()]

    # Visites par jour sur 7 jours
    par_jour_result = await db.execute(
        select(Visite.date_visite, func.count(func.distinct(CONNEXION)).label("nb"))
        .where(Visite.date_visite >= debut_semaine)
        .group_by(Visite.date_visite)
        .order_by(Visite.date_visite)
    )
    par_jour = [{"date": str(r.date_visite), "visites": r.nb} for r in par_jour_result.all()]

    return {
        # total, aujourd_hui, hier, 7_jours, 30_jours, par_jour : connexions
        "total": total,
        "connexions": total,
        "pages_vues": pages_vues,
        "visiteurs_uniques": visiteurs_uniques,
        "aujourd_hui": today_count,
        "hier": hier_count,
        "7_jours": semaine_count,
        "30_jours": mois_count,
        "top_pages": top_pages,
        "par_jour": par_jour,
    }
