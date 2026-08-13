# app/api/v1/endpoints/stats.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import select, func, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.database.session import get_db
from app.models.crasc import Crasc, Region, Osc, OscType, News
from app.models.jobs import Jobs
from app.models.key_stats import KeyStats
from app.models.users import User
from app.models.formation import Formation, FormationInscription

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

    # Count OSC (visible and not rejected)
    osc_result = await db.execute(select(func.count(Osc.id)).where(Osc.statut_publication != "rejete", Osc.is_visible == True))
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
        .outerjoin(Osc, (Osc.crasc_id == Crasc.id) & (Osc.statut_publication != "rejete") & (Osc.is_visible == True))
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
        .outerjoin(Osc, (Osc.type_id == OscType.id) & (Osc.statut_publication != "rejete") & (Osc.is_visible == True))
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
        .outerjoin(Osc, (Osc.crasc_id == Crasc.id) & (Osc.statut_publication != "rejete") & (Osc.is_visible == True))
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

    # OSC distinctes ayant au moins un inscrit (via osc_id sur la formation)
    osc_formees_res = await db.execute(
        select(func.count(func.distinct(Formation.osc_id)))
        .join(FormationInscription, FormationInscription.formation_id == Formation.id)
        .where(Formation.osc_id.isnot(None))
    )
    total_osc_formees = osc_formees_res.scalar_one()

    # Répartition des inscrits par catégorie d'acteurs
    cat_query = (
        select(
            FormationInscription.categorie_acteur.label("categorie"),
            func.count(FormationInscription.id).label("total"),
        )
        .group_by(FormationInscription.categorie_acteur)
        .order_by(desc("total"))
    )
    cat_result = await db.execute(cat_query)
    cat_rows = cat_result.all()

    par_categorie = [
        {
            "categorie": row.categorie or "Non renseigné",
            "total": row.total,
        }
        for row in cat_rows
    ]

    return {
        "total_formations": total_formations,
        "total_inscrits": total_inscrits,
        "total_osc_formees": total_osc_formees,
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
