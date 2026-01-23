# app/api/v1/endpoints/search.py
"""
Full-text search endpoints using PostgreSQL search capabilities
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import select, or_, func, text
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any, Optional
from sqlalchemy import cast, String

from app.database.session import get_db
from app.models.crasc import News, Osc, Crasc
from app.models.jobs import Jobs
from app.schemas.crasc import NewsReadDetail, OscReadDetail
from app.schemas.jobs import JobsRead

search_router = APIRouter()


@search_router.get("/")
async def global_search(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results per category"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Global search across News, OSC, and Jobs

    Returns results from multiple entities matching the search query
    """
    search_term = f"%{q}%"

    # Search News
    news_query = (
        select(News)
        .where(
            or_(
                News.title.ilike(search_term),
                News.content.ilike(search_term)
            )
        )
        .limit(limit)
    )
    news_result = await db.execute(news_query)
    news_items = news_result.scalars().all()

    # Search OSC
    osc_query = (
        select(Osc)
        .where(
            or_(
                Osc.name.ilike(search_term),
                Osc.description.ilike(search_term)
            )
        )
        .limit(limit)
    )
    osc_result = await db.execute(osc_query)
    osc_items = osc_result.scalars().all()

    # Search Jobs
    jobs_query = (
        select(Jobs)
        .where(
            or_(
                Jobs.title.ilike(search_term),
                Jobs.description.ilike(search_term)
            )
        )
        .limit(limit)
    )
    jobs_result = await db.execute(jobs_query)
    jobs_items = jobs_result.scalars().all()

    return {
        "query": q,
        "total_results": len(news_items) + len(osc_items) + len(jobs_items),
        "results": {
            "news": [
                {
                    "id": item.id,
                    "title": item.title,
                    "slug": item.slug,
                    "content_preview": item.content[:200] + "..." if item.content and len(item.content) > 200 else item.content,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "type": "news"
                }
                for item in news_items
            ],
            "osc": [
                {
                    "id": item.id,
                    "name": item.name,
                    "slug": item.slug,
                    "description_preview": item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description,
                    "type": "osc"
                }
                for item in osc_items
            ],
            "jobs": [
                {
                    "id": item.id,
                    "title": item.title,
                    "slug": item.slug,
                    "description_preview": item.description[:200] + "..." if item.description and len(item.description) > 200 else item.description,
                    "publication_date": item.publication_date.isoformat() if item.publication_date else None,
                    "is_expired": item.is_expired,
                    "type": "job"
                }
                for item in jobs_items
            ]
        }
    }


@search_router.get("/news")
async def search_news(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Advanced news search with ranking

    Searches in title and content with relevance scoring
    """
    search_term = f"%{q}%"

    # Base query with search conditions
    query = (
        select(News)
        .where(
            or_(
                News.title.ilike(search_term),
                News.content.ilike(search_term)
            )
        )
        .offset(offset)
        .limit(limit)
    )

    # Execute query
    result = await db.execute(query)
    news_items = result.scalars().all()

    # Count total matches
    count_query = (
        select(func.count(News.id))
        .where(
            or_(
                News.title.ilike(search_term),
                News.content.ilike(search_term)
            )
        )
    )
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    return {
        "query": q,
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "results": [
            {
                "id": item.id,
                "title": item.title,
                "slug": item.slug,
                "content": item.content,
                "thumbnail_path": item.thumbnail_path,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
            for item in news_items
        ]
    }


@search_router.get("/osc")
async def search_osc(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Advanced OSC search

    Searches in name and description
    """
    search_term = f"%{q}%"

    # Base query with search conditions
    query = (
        select(Osc)
        .where(
            or_(
                Osc.name.ilike(search_term),
                Osc.description.ilike(search_term),
                Osc.address.ilike(search_term)
            )
        )
        .offset(offset)
        .limit(limit)
    )

    # Execute query
    result = await db.execute(query)
    osc_items = result.scalars().all()

    # Count total matches
    count_query = (
        select(func.count(Osc.id))
        .where(
            or_(
                Osc.name.ilike(search_term),
                Osc.description.ilike(search_term),
                Osc.address.ilike(search_term)
            )
        )
    )
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    return {
        "query": q,
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "results": [
            {
                "id": item.id,
                "name": item.name,
                "slug": item.slug,
                "description": item.description,
                "address": item.address,
                "thumbnail_path": item.thumbnail_path
            }
            for item in osc_items
        ]
    }


@search_router.get("/jobs")
async def search_jobs(
    q: str = Query(..., min_length=2, description="Search query"),
    active_only: bool = Query(False, description="Only search active jobs"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Advanced jobs search

    Searches in title and description with option to filter by active status
    """
    search_term = f"%{q}%"

    # Base query with search conditions
    query = select(Jobs).where(
        or_(
            Jobs.title.ilike(search_term),
            Jobs.description.ilike(search_term)
        )
    )

    # Add active filter if requested
    if active_only:
        query = query.where(Jobs.is_expired == False)

    # Add pagination
    query = query.offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    job_items = result.scalars().all()

    # Count total matches
    count_query = select(func.count(Jobs.id)).where(
        or_(
            Jobs.title.ilike(search_term),
            Jobs.description.ilike(search_term)
        )
    )

    if active_only:
        count_query = count_query.where(Jobs.is_expired == False)

    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    return {
        "query": q,
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "active_only": active_only,
        "results": [
            {
                "id": item.id,
                "title": item.title,
                "slug": item.slug,
                "description": item.description,
                "publication_date": item.publication_date.isoformat() if item.publication_date else None,
                "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                "is_expired": item.is_expired
            }
            for item in job_items
        ]
    }


@search_router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=2, max_length=50, description="Partial search query"),
    limit: int = Query(5, ge=1, le=10, description="Maximum suggestions"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search suggestions / autocomplete

    Returns quick suggestions for autocomplete features
    """
    search_term = f"{q}%"

    # Get news titles
    news_query = (
        select(News.title, News.slug)
        .where(News.title.ilike(search_term))
        .limit(limit)
    )
    news_result = await db.execute(news_query)
    news_suggestions = news_result.all()

    # Get OSC names
    osc_query = (
        select(Osc.name, Osc.slug)
        .where(Osc.name.ilike(search_term))
        .limit(limit)
    )
    osc_result = await db.execute(osc_query)
    osc_suggestions = osc_result.all()

    # Get job titles
    jobs_query = (
        select(Jobs.title, Jobs.slug)
        .where(Jobs.title.ilike(search_term))
        .where(Jobs.is_expired == False)
        .limit(limit)
    )
    jobs_result = await db.execute(jobs_query)
    jobs_suggestions = jobs_result.all()

    return {
        "query": q,
        "suggestions": {
            "news": [
                {"title": row[0], "slug": row[1], "type": "news"}
                for row in news_suggestions
            ],
            "osc": [
                {"name": row[0], "slug": row[1], "type": "osc"}
                for row in osc_suggestions
            ],
            "jobs": [
                {"title": row[0], "slug": row[1], "type": "job"}
                for row in jobs_suggestions
            ]
        }
    }
