# app/api/v1/endpoints/stats.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import select, func, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from app.database.session import get_db
from app.models.crasc import Crasc, Region, Osc, OscType, News
from app.models.jobs import Jobs
from app.models.adhesion import DemandeAdhesion
from app.models.documentation import Documentation
from app.core.auth import get_current_staff_user
from app.models.key_stats import KeyStats
from app.models.users import User
from app.models.formation import Formation, FormationInscription
from app.schemas.formation import CATEGORIES_ACTEURS, CATEGORIES_OSC

stats_router = APIRouter()


@stats_router.get("/dashboard")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics

    Returns counts and key metrics for all main entities
    """
    # Count CRASC
    crasc_result = await db.execute(select(func.count(Crasc.id)))
    total_crasc = crasc_result.scalar_one()

    # Count Regions
    region_result = await db.execute(select(func.count(Region.id)))
    total_regions = region_result.scalar_one()

    # Count OSC (published + visible only — same filter as public directory)
    osc_result = await db.execute(select(func.count(Osc.id)).where(Osc.statut_publication == "publie", Osc.is_visible == True))
    total_osc = osc_result.scalar_one()

    # Count OSC Types
    osc_type_result = await db.execute(select(func.count(OscType.id)))
    total_osc_types = osc_type_result.scalar_one()

    # Count News
    news_result = await db.execute(select(func.count(News.id)))
    total_news = news_result.scalar_one()

    # Count Jobs
    jobs_result = await db.execute(select(func.count(Jobs.id)))
    total_jobs = jobs_result.scalar_one()

    # Count Active Jobs
    active_jobs_result = await db.execute(
        select(func.count(Jobs.id)).where(Jobs.is_expired == False)
    )
    total_active_jobs = active_jobs_result.scalar_one()

    # Count Users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar_one()

    # Get recent news count (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_news_result = await db.execute(
        select(func.count(News.id)).where(News.created_at >= thirty_days_ago)
    )
    recent_news_count = recent_news_result.scalar_one()

    # Get recent jobs count (last 30 days)
    recent_jobs_result = await db.execute(
        select(func.count(Jobs.id)).where(Jobs.publication_date >= thirty_days_ago)
    )
    recent_jobs_count = recent_jobs_result.scalar_one()

    return {
        "crasc": {
            "total": total_crasc
        },
        "regions": {
            "total": total_regions
        },
        "osc": {
            "total": total_osc,
            "types": total_osc_types
        },
        "news": {
            "total": total_news,
            "recent_30_days": recent_news_count
        },
        "jobs": {
            "total": total_jobs,
            "active": total_active_jobs,
            "recent_30_days": recent_jobs_count
        },
        "users": {
            "total": total_users
        }
    }


@stats_router.get("/osc-by-region")
async def get_osc_by_region(
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get OSC count grouped by region

    Returns list of regions with their OSC counts
    """
    query = (
        select(
            Region.id,
            Region.name,
            Region.slug,
            func.count(Osc.id).label("osc_count")
        )
        .outerjoin(Crasc, Region.crasc_id == Crasc.id)
        .outerjoin(Osc, (Osc.crasc_id == Crasc.id) & (Osc.statut_publication == "publie") & (Osc.is_visible == True))
        .group_by(Region.id, Region.name, Region.slug)
        .order_by(desc("osc_count"))
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "region_id": row.id,
            "region_name": row.name,
            "region_slug": row.slug,
            "osc_count": row.osc_count
        }
        for row in rows
    ]


@stats_router.get("/osc-by-type")
async def get_osc_by_type(
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get OSC count grouped by type

    Returns list of OSC types with their counts
    """
    query = (
        select(
            OscType.id,
            OscType.name,
            OscType.slug,
            func.count(Osc.id).label("osc_count")
        )
        .outerjoin(Osc, (Osc.type_id == OscType.id) & (Osc.statut_publication == "publie") & (Osc.is_visible == True))
        .group_by(OscType.id, OscType.name, OscType.slug)
        .order_by(desc("osc_count"))
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "type_id": row.id,
            "type_name": row.name,
            "type_slug": row.slug,
            "osc_count": row.osc_count
        }
        for row in rows
    ]


@stats_router.get("/osc-by-crasc")
async def get_osc_by_crasc(
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get OSC count grouped by CRASC

    Returns list of CRASC with their OSC counts
    """
    query = (
        select(
            Crasc.id,
            Crasc.name,
            Crasc.slug,
            func.count(Osc.id).label("osc_count")
        )
        .outerjoin(Osc, (Osc.crasc_id == Crasc.id) & (Osc.statut_publication == "publie") & (Osc.is_visible == True))
        .group_by(Crasc.id, Crasc.name, Crasc.slug)
        .order_by(desc("osc_count"))
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "crasc_id": row.id,
            "crasc_name": row.name,
            "crasc_slug": row.slug,
            "osc_count": row.osc_count
        }
        for row in rows
    ]


@stats_router.get("/news-activity")
async def get_news_activity(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get news activity statistics

    - **days**: Number of days to analyze (default: 30, max: 365)

    Returns news counts by CRASC and OSC for the specified period
    """
    start_date = datetime.now() - timedelta(days=days)

    # News count by CRASC
    crasc_query = (
        select(
            Crasc.id,
            Crasc.name,
            Crasc.slug,
            func.count(News.id).label("news_count")
        )
        .outerjoin(News, News.crasc_id == Crasc.id)
        .where(News.created_at >= start_date)
        .group_by(Crasc.id, Crasc.name, Crasc.slug)
        .order_by(desc("news_count"))
    )

    crasc_result = await db.execute(crasc_query)
    crasc_rows = crasc_result.all()

    # News count by OSC
    osc_query = (
        select(
            Osc.id,
            Osc.name,
            Osc.slug,
            func.count(News.id).label("news_count")
        )
        .outerjoin(News, News.osc_id == Osc.id)
        .where(News.created_at >= start_date)
        .group_by(Osc.id, Osc.name, Osc.slug)
        .order_by(desc("news_count"))
        .limit(10)  # Top 10 most active OSCs
    )

    osc_result = await db.execute(osc_query)
    osc_rows = osc_result.all()

    # Total news in period
    total_result = await db.execute(
        select(func.count(News.id)).where(News.created_at >= start_date)
    )
    total_news = total_result.scalar_one()

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "total_news": total_news,
        "by_crasc": [
            {
                "crasc_id": row.id,
                "crasc_name": row.name,
                "crasc_slug": row.slug,
                "news_count": row.news_count
            }
            for row in crasc_rows
        ],
        "top_osc": [
            {
                "osc_id": row.id,
                "osc_name": row.name,
                "osc_slug": row.slug,
                "news_count": row.news_count
            }
            for row in osc_rows
        ]
    }


@stats_router.get("/jobs-trends")
async def get_jobs_trends(
    days: int = Query(90, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get job posting trends and statistics

    - **days**: Number of days to analyze (default: 90, max: 365)

    Returns job statistics including active, expired, and recent postings
    """
    start_date = datetime.now() - timedelta(days=days)

    # Total jobs in period
    total_result = await db.execute(
        select(func.count(Jobs.id)).where(Jobs.publication_date >= start_date)
    )
    total_jobs = total_result.scalar_one()

    # Active jobs
    active_result = await db.execute(
        select(func.count(Jobs.id))
        .where(Jobs.publication_date >= start_date)
        .where(Jobs.is_expired == False)
    )
    active_jobs = active_result.scalar_one()

    # Expired jobs
    expired_result = await db.execute(
        select(func.count(Jobs.id))
        .where(Jobs.publication_date >= start_date)
        .where(Jobs.is_expired == True)
    )
    expired_jobs = expired_result.scalar_one()

    # Recent jobs (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count(Jobs.id)).where(Jobs.publication_date >= seven_days_ago)
    )
    recent_jobs = recent_result.scalar_one()

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "expired_jobs": expired_jobs,
        "recent_7_days": recent_jobs,
        "active_percentage": round((active_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2)
    }


@stats_router.get("/formations")
async def get_formation_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Statistiques des formations : total inscrits, OSC formées, répartition par catégorie d'acteurs."""

    # Total formations publiées
    total_formations_res = await db.execute(
        select(func.count(Formation.id)).where(Formation.is_published == True)
    )
    total_formations = total_formations_res.scalar_one()

    # Total inscrits (toutes formations confondues)
    total_inscrits_res = await db.execute(select(func.count(FormationInscription.id)))
    total_inscrits = total_inscrits_res.scalar_one()

    # OSC formées : inscrits de la catégorie « Organisation de la Société Civile »
    # (le même chiffre que la barre OSC de la répartition ci-dessous ; l'ancien
    # calcul comptait les OSC organisatrices des formations, d'où « 1 »)
    osc_formees_res = await db.execute(
        select(func.count(FormationInscription.id))
        .where(FormationInscription.categorie_acteur.in_(CATEGORIES_OSC))
    )
    total_osc_formees = osc_formees_res.scalar_one()

    # Répartition des inscrits par public formé : les 4 catégories d'acteurs,
    # toujours affichées (même à 0). Les anciennes inscriptions « OSC » comptent
    # avec les OSC ; celles d'avant le champ obligatoire (sans catégorie) ne
    # figurent pas dans la répartition (« Non renseigné » retiré à la demande PdoC).
    cat_result = await db.execute(
        select(
            FormationInscription.categorie_acteur.label("categorie"),
            func.count(FormationInscription.id).label("total"),
        )
        .where(FormationInscription.categorie_acteur.is_not(None))
        .group_by(FormationInscription.categorie_acteur)
    )
    totaux = {categorie: 0 for categorie in CATEGORIES_ACTEURS}
    for row in cat_result.all():
        categorie = CATEGORIES_ACTEURS[0] if row.categorie in CATEGORIES_OSC else row.categorie
        if categorie in totaux:
            totaux[categorie] += row.total
    par_categorie = [{"categorie": c, "total": t} for c, t in totaux.items()]

    return {
        "total_formations": total_formations,
        "total_inscrits": total_inscrits,
        "total_osc_formees": total_osc_formees,
        "total_grand_public_forme": totaux["Grand public"],
        "par_categorie_acteur": par_categorie,
    }


@stats_router.get("/key-stats")
async def get_key_stats_summary(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summary of all key statistics configured in the system

    Returns all KeyStats entries with their values
    """
    result = await db.execute(
        select(KeyStats).order_by(KeyStats.id)
    )
    key_stats = result.scalars().all()

    return {
        "total_stats": len(key_stats),
        "stats": [
            {
                "id": stat.id,
                "name": stat.name,
                "value": stat.value,
                "description": stat.description
            }
            for stat in key_stats
        ]
    }


# ── Tableau de bord du back-office : compteurs et activités récentes ──

def _date_utc(valeur: Optional[datetime]) -> Optional[datetime]:
    """Dates avec ou sans fuseau (selon les tables) rendues comparables."""
    if valeur is None:
        return None
    return valeur if valeur.tzinfo else valeur.replace(tzinfo=timezone.utc)


@stats_router.get("/back-office")
async def get_back_office_stats(
    limite: int = Query(8, ge=1, le=50, description="Nombre d'activités récentes"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
) -> Dict[str, Any]:
    """
    Compteurs et activités récentes réels du tableau de bord (staff). Un admin
    CRASC ne voit que ce qui concerne son CRASC (OSC, actualités, demandes
    d'adhésion, formations).
    """
    crasc = None
    if not current_user.is_superuser and current_user.crasc_id:
        crasc = await db.get(Crasc, current_user.crasc_id)

    def portee(colonne_crasc):
        return [colonne_crasc == crasc.id] if crasc else []

    adhesions_portee = [DemandeAdhesion.crasc_nom.ilike(f"%{crasc.name}%")] if crasc else []

    async def compter(*conditions) -> int:
        return (await db.execute(select(func.count()).where(*conditions))).scalar_one()

    compteurs = {
        "actualites_publiees": await compter(News.statut_publication == "publie", *portee(News.crasc_id)),
        "actualites_en_attente": await compter(News.statut_publication == "en_attente", *portee(News.crasc_id)),
        "adhesions_en_attente": await compter(DemandeAdhesion.statut == "en_attente", *adhesions_portee),
        "adhesions_total": await compter(DemandeAdhesion.id.is_not(None), *adhesions_portee),
        "offres_emploi_actives": await compter(Jobs.is_expired == False, Jobs.statut_publication == "publie"),
    }

    activites: List[Dict[str, Any]] = []

    def ajouter(type_, titre, detail, date, lien):
        if date:
            activites.append({"type": type_, "titre": titre, "detail": detail, "date": _date_utc(date), "lien": lien})

    for o in (await db.execute(
        select(Osc).where(*portee(Osc.crasc_id)).order_by(desc(Osc.created_at)).limit(limite)
    )).scalars():
        ajouter("osc", "Nouvelle OSC enregistrée", f"{o.name} a été ajoutée", o.created_at,
                f"/admin/gestion-des-crasc/osc/{o.slug}" if o.slug else "/admin/gestion-des-crasc/osc")

    for d in (await db.execute(
        select(DemandeAdhesion).where(*adhesions_portee).order_by(desc(DemandeAdhesion.created_at)).limit(limite)
    )).scalars():
        ajouter("adhesion", "Demande d'adhésion", d.nom_organisation, d.created_at, "/admin/demandes-adhesion")

    for n in (await db.execute(
        select(News).where(News.statut_publication.in_(("publie", "en_attente")), *portee(News.crasc_id))
        .order_by(desc(News.created_at)).limit(limite)
    )).scalars():
        en_attente = n.statut_publication == "en_attente"
        ajouter("actualite", "Actualité à valider" if en_attente else "Actualité publiée", n.title, n.created_at,
                "/admin/moderation" if en_attente else f"/admin/gestion-des-actualites/{n.slug}/modifier")

    for f in (await db.execute(
        select(Formation).where(*portee(Formation.crasc_id)).order_by(desc(Formation.created_at)).limit(limite)
    )).scalars():
        ajouter("formation", "Formation ajoutée", f.title, f.created_at, f"/admin/formations/{f.slug}/modifier")

    if not crasc:
        for j in (await db.execute(
            select(Jobs).where(Jobs.statut_publication == "publie").order_by(desc(Jobs.created_at)).limit(limite)
        )).scalars():
            ajouter("emploi", "Offre d'emploi publiée", f"{j.title} - {j.employer}", j.publication_date or j.created_at,
                    f"/admin/emplois/{j.slug}/modifier" if j.slug else "/admin/emplois")

        for u in (await db.execute(
            select(User).order_by(desc(User.date_joined)).limit(limite)
        )).scalars():
            ajouter("utilisateur", "Nouvel utilisateur", f"{u.full_name or u.email} a créé un compte", u.date_joined,
                    "/admin/utilisateurs")

        for r in (await db.execute(
            select(Documentation).order_by(desc(Documentation.created_at)).limit(limite)
        )).scalars():
            ajouter("ressource", "Ressource ajoutée", r.title, r.created_at,
                    f"/admin/ressources/{r.slug}/modifier" if r.slug else "/admin/ressources")

    activites.sort(key=lambda a: a["date"], reverse=True)
    return {"compteurs": compteurs, "activites": activites[:limite]}
