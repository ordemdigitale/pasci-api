# app/api/v1/endpoints/tags.py
"""
Tags/Categories endpoints for News organization
"""
import slugify
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.database.session import get_db
from app.models.tags import Tag, NewsTag
from app.schemas.tags import TagCreate, TagRead, TagUpdate, TagWithNewsCount

tags_router = APIRouter()


@tags_router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db)
) -> Tag:
    """
    Create a new tag/category

    - **name**: Tag name (required, unique)
    - **description**: Optional description
    - **color**: Hex color code (default: #3B82F6)
    """
    # Check for duplicate name
    result = await db.execute(select(Tag).where(Tag.name == tag.name))
    existing_tag = result.scalars().first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "duplicate_error",
                "errors": [{
                    "field": "name",
                    "message": f"Un tag avec le nom '{tag.name}' existe déjà."
                }]
            }
        )

    try:
        db_tag = Tag(**tag.model_dump())
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)
        return db_tag
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "database_error",
                "errors": [{
                    "field": "database",
                    "message": f"Erreur lors de la création du tag: {str(e)}"
                }]
            }
        )


@tags_router.get("", response_model=List[TagWithNewsCount], status_code=status.HTTP_200_OK)
async def get_tags(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tags with news count

    Returns all tags ordered by name with the count of associated news articles
    """
    # Get all tags
    tags_query = (
        select(Tag)
        .offset(skip)
        .limit(limit)
        .order_by(Tag.name)
    )
    tags_result = await db.execute(tags_query)
    tags = tags_result.scalars().all()

    # Get news count for each tag
    result_list = []
    for tag in tags:
        count_query = select(func.count(NewsTag.news_id)).where(NewsTag.tag_id == tag.id)
        count_result = await db.execute(count_query)
        news_count = count_result.scalar_one()

        result_list.append({
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "color": tag.color,
            "created_at": tag.created_at,
            "news_count": news_count
        })

    return result_list


@tags_router.get("/{tag_slug}", response_model=TagWithNewsCount, status_code=status.HTTP_200_OK)
async def get_tag(
    tag_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single tag by slug with news count
    """
    result = await db.execute(select(Tag).where(Tag.slug == tag_slug))
    tag = result.scalars().first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag non trouvé."
        )

    # Get news count
    count_query = select(func.count(NewsTag.news_id)).where(NewsTag.tag_id == tag.id)
    count_result = await db.execute(count_query)
    news_count = count_result.scalar_one()

    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "description": tag.description,
        "color": tag.color,
        "created_at": tag.created_at,
        "news_count": news_count
    }


@tags_router.patch("/{tag_slug}", response_model=TagRead, status_code=status.HTTP_200_OK)
async def update_tag(
    tag_slug: str,
    tag_update: TagUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a tag

    All fields are optional
    """
    # Fetch existing tag
    result = await db.execute(select(Tag).where(Tag.slug == tag_slug))
    tag = result.scalars().first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag non trouvé."
        )

    # Check for name conflict if name is being updated
    update_data = tag_update.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != tag.name:
        check_result = await db.execute(
            select(Tag).where(Tag.name == update_data["name"])
        )
        if check_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "duplicate_error",
                    "errors": [{
                        "field": "name",
                        "message": f"Un tag avec le nom '{update_data['name']}' existe déjà."
                    }]
                }
            )

    # Update fields
    for key, value in update_data.items():
        setattr(tag, key, value)

    # Update slug if name changed
    if "name" in update_data:
        tag.slug = slugify.slugify(tag.name)

    try:
        await db.commit()
        await db.refresh(tag)
        return tag
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "database_error",
                "errors": [{
                    "field": "database",
                    "message": f"Erreur lors de la mise à jour: {str(e)}"
                }]
            }
        )


@tags_router.delete("/{tag_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a tag

    This will also remove all associations with news articles
    """
    result = await db.execute(select(Tag).where(Tag.slug == tag_slug))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag '{tag_slug}' non trouvé."
        )

    try:
        await db.delete(tag)
        await db.commit()
        return None
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "database_error",
                "errors": [{
                    "field": "database",
                    "message": f"Erreur lors de la suppression: {str(e)}"
                }]
            }
        )
