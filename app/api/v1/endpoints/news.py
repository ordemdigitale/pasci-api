# app/api/v1/endpoints/news.py | News endpoints
import os
import uuid
from datetime import datetime
from typing import Optional, List

import slugify
from fastapi import APIRouter, HTTPException, status, UploadFile, Depends, File, Form, Query
from PIL import Image
from sqlalchemy.orm import selectinload
from sqlmodel import desc, select, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.schemas.crasc import (
    NewsRead,
    NewsReadDetail,
    NewsUpdate
)
from app.models.crasc import News
from app.models.users import User
from app.core.auth import get_current_staff_user, get_current_redacteur_or_staff, get_current_redacteur_crasc_or_staff, get_optional_current_user

news_router = APIRouter()

# Configuration for image uploads
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
THUMBNAIL_SIZE = (800, 600)  # Max dimensions for thumbnails


def validate_and_process_image(file: UploadFile) -> str:
    """
    Validate and process uploaded image
    Returns the saved filename
    Raises HTTPException if validation fails
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "thumbnail",
                    "message": "Aucun fichier fourni."
                }]
            }
        )

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "thumbnail",
                    "message": f"Format d'image invalide. Formats acceptés: {', '.join(ALLOWED_EXTENSIONS)}."
                }]
            }
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "thumbnail",
                    "message": f"Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE // (1024*1024)}MB."
                }]
            }
        )

    # Generate unique filename
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Save and optimize image
    try:
        with Image.open(file.file) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Resize if too large
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Save with optimization
            img.save(file_path, optimize=True, quality=85)

        return filename
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "processing_error",
                "errors": [{
                    "field": "thumbnail",
                    "message": f"Erreur lors du traitement de l'image: {str(e)}"
                }]
            }
        )


@news_router.post("", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
async def create_news(
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
    crasc_id: str = Form(""),
    osc_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_redacteur_or_staff),
):
    """
    Create a new news article

    - **title**: Title of the news article (required)
    - **content**: Content of the article
    - **thumbnail**: Image file (optional, max 5MB)
    - **crasc_id**: Associated CRASC ID
    - **osc_id**: Associated OSC ID
    """
    # Validate title
    if not title or not title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "title",
                    "message": "Le titre est requis et ne peut pas être vide."
                }]
            }
        )
    
    # Parse IDs
    crasc_id_int = int(crasc_id) if crasc_id and crasc_id != "" else None
    osc_id_int = int(osc_id) if osc_id and osc_id != "" else None

    # Rédacteur CRASC : forcer son propre CRASC
    if current_user.is_redacteur and not current_user.is_staff and not current_user.is_superuser:
        crasc_id_int = current_user.crasc_id

    # Handle image upload
    if thumbnail and thumbnail.filename:
        saved_path = validate_and_process_image(thumbnail)
    else:
        saved_path = "default.png"

    # Si rédacteur → en attente de validation, si staff → publié directement
    statut = "publie" if current_user.is_staff else "en_attente"

    # Create database record
    news_create = News(
        title=title.strip(),
        content=content,
        crasc_id=crasc_id_int,
        osc_id=osc_id_int,
        thumbnail_path=saved_path,
        statut_publication=statut,
    )

    # Check for duplicate title
    result = await db.execute(select(News).where(News.title == news_create.title))
    existing_news = result.scalars().first()
    if existing_news:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "duplicate_error",
                "errors": [{
                    "field": "title",
                    "message": "Une actualité avec ce titre existe déjà."
                }]
            }
        )

    try:
        db.add(news_create)
        await db.commit()
        await db.refresh(news_create)
        return news_create
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "database_error",
                "errors": [{
                    "field": "database",
                    "message": f"Erreur lors de la création: {str(e)}"
                }]
            }
        )


@news_router.get("", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
async def get_all_news(
    skip: int = Query(0, ge=0, description="Nombre d'articles à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'articles à retourner"),
    crasc_id: Optional[int] = Query(None, description="Filtrer par CRASC ID"),
    osc_id: Optional[int] = Query(None, description="Filtrer par OSC ID"),
    search: Optional[str] = Query(None, description="Rechercher dans titre/contenu"),
    sort_by: str = Query("created_at", description="Champ de tri (created_at, title)"),
    sort_order: str = Query("desc", description="Ordre de tri (asc, desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all news articles with filtering and pagination

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max 100)
    - **crasc_id**: Filter by CRASC
    - **osc_id**: Filter by OSC
    - **search**: Search in title and content
    - **sort_by**: Sort field (created_at, title)
    - **sort_order**: Sort order (asc, desc)
    """
    # Base query with relationships — public : uniquement publiés
    query = select(News).options(
        selectinload(News.crasc),
        selectinload(News.osc)
    ).where(News.statut_publication == "publie")

    # Apply filters
    if crasc_id:
        query = query.where(News.crasc_id == crasc_id)

    if osc_id:
        query = query.where(News.osc_id == osc_id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                News.title.ilike(search_term),
                News.content.ilike(search_term)
            )
        )

    # Apply sorting
    if sort_by == "title":
        order_column = News.title
    else:  # default to created_at
        order_column = News.created_at

    if sort_order == "asc":
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    news_list = result.scalars().all()

    return news_list


@news_router.get("/spotlight", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
async def get_spotlight_news_per_crasc(db: AsyncSession = Depends(get_db)):
    """
    Get spotlight news - one latest news per CRASC
    Useful for homepage/dashboard displays
    """
    query = (
        select(News)
        .distinct(News.crasc_id)
        .where(News.crasc_id.is_not(None), News.statut_publication == "publie")
        .options(selectinload(News.crasc), selectinload(News.osc))
        .order_by(News.crasc_id, News.id.desc())
    )

    result = await db.execute(query)
    news_items = result.unique().scalars().all()

    return news_items


@news_router.get("/recent", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
async def get_recent_news(
    limit: int = Query(5, ge=1, le=20, description="Nombre d'articles récents"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most recent news articles
    """
    query = (
        select(News)
        .where(News.statut_publication == "publie")
        .options(selectinload(News.crasc), selectinload(News.osc))
        .order_by(desc(News.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    news_list = result.scalars().all()

    return news_list


@news_router.get("/{news_slug}", response_model=NewsReadDetail, status_code=status.HTTP_200_OK)
async def get_single_news(
    news_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Get a single news article by slug
    """
    query = select(News).where(News.slug == news_slug).options(
        selectinload(News.crasc),
        selectinload(News.osc)
    )

    result = await db.execute(query)
    news = result.scalar_one_or_none()

    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actualité non trouvée."
        )
    can_view_pending = bool(
        current_user
        and (
            current_user.is_staff
            or current_user.is_superuser
            or (current_user.is_redacteur and current_user.crasc_id == news.crasc_id)
        )
    )
    if news.statut_publication != "publie" and not can_view_pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité non trouvée.")

    return news


async def get_news_update_form(
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    crasc_id: str = Form(""),
    osc_id: str = Form("")
) -> NewsUpdate:
    """Parse form data into NewsUpdate"""
    # Only include fields that are actually provided
    update_dict = {}
    
    if title is not None:
        update_dict["title"] = title
    
    if content is not None:
        update_dict["content"] = content
    
    # Parse IDs - only include if provided
    if crasc_id and crasc_id != "":
        update_dict["crasc_id"] = int(crasc_id)
    
    if osc_id and osc_id != "":
        update_dict["osc_id"] = int(osc_id)
    
    return NewsUpdate(**update_dict)


@news_router.patch("/{news_slug}", response_model=NewsReadDetail, status_code=status.HTTP_200_OK)
async def update_news(
    news_slug: str,
    news_update: NewsUpdate = Depends(get_news_update_form),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_redacteur_crasc_or_staff),
):
    """
    Update a news article

    - **title**: New title (optional)
    - **content**: New content (optional)
    - **thumbnail**: New image (optional)
    - **crasc_id**: New CRASC association (optional)
    - **osc_id**: New OSC association (optional)
    """
    # Fetch existing news
    result = await db.execute(
        select(News).where(News.slug == news_slug).options(
            selectinload(News.crasc),
            selectinload(News.osc)
        )
    )
    news = result.scalars().first()

    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actualité non trouvée."
        )

    # Rédacteur CRASC : vérifier l'appartenance
    is_redacteur_only = current_user.is_redacteur and not current_user.is_staff and not current_user.is_superuser
    if current_user.is_redacteur and not current_user.is_staff and not current_user.is_superuser:
        if news.crasc_id != current_user.crasc_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez modifier que les actualités de votre CRASC."
            )

    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
        saved_path = validate_and_process_image(thumbnail)
        news.thumbnail_path = saved_path

    # Update other fields (only fields that were provided in the form)
    update_data = news_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(news, key, value)
    if is_redacteur_only:
        news.statut_publication = "en_attente"

    # Update slug if title changed
    if "title" in update_data:
        news.slug = slugify.slugify(news.title)

    # Update timestamp
    news.updated_at = datetime.now()

    try:
        await db.commit()
        await db.refresh(news)
        return news
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


@news_router.get("/admin/en-attente", response_model=List[NewsReadDetail])
async def list_news_en_attente(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Liste toutes les actualités en attente de validation (staff only)."""
    query = select(News).where(News.statut_publication == "en_attente").options(selectinload(News.crasc), selectinload(News.osc)).order_by(News.created_at.asc())
    if not current_user.is_superuser:
        query = query.where(News.crasc_id == current_user.crasc_id)
    result = await db.execute(query)
    return result.scalars().all()


@news_router.patch("/{news_slug}/valider", response_model=NewsReadDetail)
async def valider_news(
    news_slug: str,
    action: str = Query(..., description="publie ou rejete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Approuver ou rejeter une actualité (staff only)."""
    if action not in ("publie", "rejete"):
        raise HTTPException(status_code=400, detail="Action invalide. Utilisez 'publie' ou 'rejete'.")
    result = await db.execute(
        select(News).where(News.slug == news_slug).options(selectinload(News.crasc), selectinload(News.osc))
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Actualité non trouvée.")
    news.statut_publication = action
    news.updated_at = datetime.now()
    await db.commit()
    await db.refresh(news)
    return news


@news_router.delete("/{news_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """
    Delete a news article by slug (staff only)
    """
    result = await db.execute(select(News).where(News.slug == news_slug))
    news = result.scalar_one_or_none()

    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Actualité '{news_slug}' non trouvée."
        )

    await db.delete(news)
    await db.commit()
    return None
