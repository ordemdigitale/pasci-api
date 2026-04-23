import hashlib
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Request
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


@visites_router.post("", status_code=204)
async def enregistrer_visite(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Enregistre une visite de page.
    Body JSON attendu : { "path": "/formations" }
    Déduplication : 1 visite max par IP + path + jour.
    """
    try:
        body = await request.json()
        path = str(body.get("path", "/"))[:500]
    except Exception:
        path = "/"

    ip = _get_client_ip(request)
    ip_hash = _hash_ip(ip)
    today = date.today()

    # Vérifier si déjà enregistré aujourd'hui pour ce path + IP
    existing = await db.execute(
        select(Visite).where(
            Visite.ip_hash == ip_hash,
            Visite.path == path,
            Visite.date_visite == today,
        )
    )
    if existing.scalar_one_or_none():
        return  # Déjà compté

    visite = Visite(path=path, ip_hash=ip_hash, date_visite=today)
    db.add(visite)
    await db.commit()


@visites_router.get("/stats")
async def get_stats_visites(db: AsyncSession = Depends(get_db)):
    """Retourne les statistiques de visites pour le dashboard admin."""
    today = date.today()
    hier = today - timedelta(days=1)
    debut_semaine = today - timedelta(days=6)
    debut_mois = today - timedelta(days=29)

    # Total visites (toutes)
    total = (await db.execute(select(func.count(Visite.id)))).scalar_one()

    # Visites uniques (par ip_hash distinct)
    visiteurs_uniques = (await db.execute(
        select(func.count(func.distinct(Visite.ip_hash)))
    )).scalar_one()

    # Aujourd'hui
    today_count = (await db.execute(
        select(func.count(Visite.id)).where(Visite.date_visite == today)
    )).scalar_one()

    # Hier
    hier_count = (await db.execute(
        select(func.count(Visite.id)).where(Visite.date_visite == hier)
    )).scalar_one()

    # 7 derniers jours
    semaine_count = (await db.execute(
        select(func.count(Visite.id)).where(Visite.date_visite >= debut_semaine)
    )).scalar_one()

    # 30 derniers jours
    mois_count = (await db.execute(
        select(func.count(Visite.id)).where(Visite.date_visite >= debut_mois)
    )).scalar_one()

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
        select(Visite.date_visite, func.count(Visite.id).label("nb"))
        .where(Visite.date_visite >= debut_semaine)
        .group_by(Visite.date_visite)
        .order_by(Visite.date_visite)
    )
    par_jour = [{"date": str(r.date_visite), "visites": r.nb} for r in par_jour_result.all()]

    return {
        "total": total,
        "visiteurs_uniques": visiteurs_uniques,
        "aujourd_hui": today_count,
        "hier": hier_count,
        "7_jours": semaine_count,
        "30_jours": mois_count,
        "top_pages": top_pages,
        "par_jour": par_jour,
    }
