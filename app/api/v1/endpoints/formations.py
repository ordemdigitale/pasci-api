# app/api/v1/endpoints/formations.py
"""
Formations/Training endpoints
"""
import os
import shutil
import uuid
import slugify
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, UploadFile, Depends, File, Form, Query
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.core.config import settings
from app.database.session import get_db
from app.models.formation import Formation
from app.schemas.formation import FormationCreate, FormationRead, FormationUpdate, FormationReadWithRelations

formations_router = APIRouter()


@formations_router.post("", response_model=FormationRead, status_code=status.HTTP_201_CREATED)
async def create_formation(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    trainer: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),  # Format: YYYY-MM-DD HH:MM
    end_date: Optional[str] = Form(None),
    registration_deadline: Optional[str] = Form(None),
    max_participants: Optional[int] = Form(None),
    registration_link: Optional[str] = Form(None),
    materials_link: Optional[str] = Form(None),
    is_published: bool = Form(False),
    crasc_id: str = Form(""),
    osc_id: str = Form(""),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
) -> Formation:
    """
    Create a new formation/training

    - **title**: Title of the formation (required)
    - **description**: Detailed description
    - **trainer**: Trainer name
    - **location**: Training location
    - **start_date**: Start date (YYYY-MM-DD HH:MM)
    - **end_date**: End date
    - **registration_deadline**: Registration deadline
    - **max_participants**: Maximum number of participants
    - **thumbnail**: Image file
    - **crasc_id**: Associated CRASC
    - **osc_id**: Associated OSC
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

    # Parse dates
    start_date_parsed = datetime.fromisoformat(start_date) if start_date else None
    end_date_parsed = datetime.fromisoformat(end_date) if end_date else None
    registration_deadline_parsed = datetime.fromisoformat(registration_deadline) if registration_deadline else None

    # Handle image upload
    saved_path = "default.png"
    if thumbnail and thumbnail.filename:
        file_extension = thumbnail.filename.split(".")[-1].lower()
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "validation_error",
                    "errors": [{
                        "field": "thumbnail",
                        "message": f"Format d'image invalide. Formats acceptés: {', '.join(allowed_extensions)}."
                    }]
                }
            )
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        saved_path = filename

    # Check for duplicate title
    result = await db.execute(select(Formation).where(Formation.title == title.strip()))
    existing_formation = result.scalars().first()
    if existing_formation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "duplicate_error",
                "errors": [{
                    "field": "title",
                    "message": f"Une formation avec le titre '{title.strip()}' existe déjà."
                }]
            }
        )

    try:
        formation = Formation(
            title=title.strip(),
            description=description,
            trainer=trainer,
            location=location,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            registration_deadline=registration_deadline_parsed,
            max_participants=max_participants,
            registration_link=registration_link,
            materials_link=materials_link,
            is_published=is_published,
            crasc_id=crasc_id_int,
            osc_id=osc_id_int,
            thumbnail_path=saved_path
        )
        db.add(formation)
        await db.commit()
        await db.refresh(formation)
        return formation
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


@formations_router.get("", response_model=List[FormationReadWithRelations], status_code=status.HTTP_200_OK)
async def get_formations(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'enregistrements à retourner"),
    published_only: bool = Query(False, description="Afficher uniquement les formations publiées"),
    upcoming_only: bool = Query(False, description="Afficher uniquement les formations à venir"),
    search: Optional[str] = Query(None, description="Rechercher dans titre/description"),
    crasc_id: Optional[int] = Query(None, description="Filtrer par CRASC"),
    osc_id: Optional[int] = Query(None, description="Filtrer par OSC"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all formations with filtering and pagination

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (max 100)
    - **published_only**: Show only published formations
    - **upcoming_only**: Show only upcoming formations
    - **search**: Search in title and description
    - **crasc_id**: Filter by CRASC
    - **osc_id**: Filter by OSC
    """
    query = select(Formation).options(
        selectinload(Formation.crasc),
        selectinload(Formation.osc)
    )

    # Apply filters
    if published_only:
        query = query.where(Formation.is_published == True)

    if upcoming_only:
        query = query.where(Formation.start_date >= datetime.now())
        query = query.where(Formation.is_completed == False)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Formation.title.ilike(search_term),
                Formation.description.ilike(search_term)
            )
        )

    if crasc_id:
        query = query.where(Formation.crasc_id == crasc_id)

    if osc_id:
        query = query.where(Formation.osc_id == osc_id)

    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Formation.start_date.desc())

    result = await db.execute(query)
    formations = result.scalars().all()
    return formations


@formations_router.get("/upcoming", response_model=List[FormationRead], status_code=status.HTTP_200_OK)
async def get_upcoming_formations(
    limit: int = Query(5, ge=1, le=20, description="Nombre de formations à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get upcoming published formations

    Returns the next upcoming published formations
    """
    query = (
        select(Formation)
        .where(Formation.is_published == True)
        .where(Formation.is_completed == False)
        .where(Formation.start_date >= datetime.now())
        .order_by(Formation.start_date.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    formations = result.scalars().all()
    return formations


@formations_router.get("/{formation_slug}", response_model=FormationReadWithRelations, status_code=status.HTTP_200_OK)
async def get_formation(
    formation_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single formation by slug with related CRASC and OSC
    """
    query = select(Formation).where(Formation.slug == formation_slug).options(
        selectinload(Formation.crasc),
        selectinload(Formation.osc)
    )

    result = await db.execute(query)
    formation = result.scalars().first()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formation non trouvée."
        )

    return formation


async def get_formation_update_form(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    trainer: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    registration_deadline: Optional[str] = Form(None),
    max_participants: Optional[int] = Form(None),
    current_participants: Optional[int] = Form(None),
    registration_link: Optional[str] = Form(None),
    materials_link: Optional[str] = Form(None),
    is_published: Optional[bool] = Form(None),
    is_full: Optional[bool] = Form(None),
    is_completed: Optional[bool] = Form(None),
    crasc_id: str = Form(""),
    osc_id: str = Form("")
) -> FormationUpdate:
    """Parse form data into FormationUpdate"""
    # Only include fields that are actually provided
    update_dict = {}
    
    if title is not None:
        update_dict["title"] = title
    
    if description is not None:
        update_dict["description"] = description
    
    if trainer is not None:
        update_dict["trainer"] = trainer
    
    if location is not None:
        update_dict["location"] = location
    
    # Parse dates only if provided
    if start_date:
        update_dict["start_date"] = datetime.fromisoformat(start_date)
    
    if end_date:
        update_dict["end_date"] = datetime.fromisoformat(end_date)
    
    if registration_deadline:
        update_dict["registration_deadline"] = datetime.fromisoformat(registration_deadline)
    
    if max_participants is not None:
        update_dict["max_participants"] = max_participants
    
    if current_participants is not None:
        update_dict["current_participants"] = current_participants
    
    if registration_link is not None:
        update_dict["registration_link"] = registration_link
    
    if materials_link is not None:
        update_dict["materials_link"] = materials_link
    
    if is_published is not None:
        update_dict["is_published"] = is_published
    
    if is_full is not None:
        update_dict["is_full"] = is_full
    
    if is_completed is not None:
        update_dict["is_completed"] = is_completed
    
    # Parse IDs - only include if provided
    if crasc_id and crasc_id != "":
        update_dict["crasc_id"] = int(crasc_id)
    
    if osc_id and osc_id != "":
        update_dict["osc_id"] = int(osc_id)
    
    return FormationUpdate(**update_dict)


@formations_router.patch("/{formation_slug}", response_model=FormationReadWithRelations, status_code=status.HTTP_200_OK)
async def update_formation(
    formation_slug: str,
    formation_update: FormationUpdate = Depends(get_formation_update_form),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a formation

    All fields are optional
    """
    # Fetch existing formation
    result = await db.execute(
        select(Formation).where(Formation.slug == formation_slug).options(
            selectinload(Formation.crasc),
            selectinload(Formation.osc)
        )
    )
    formation = result.scalars().first()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formation non trouvée."
        )

    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
        file_extension = thumbnail.filename.split(".")[-1].lower()
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format d'image invalide. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        formation.thumbnail_path = filename

    # Update other fields
    update_data = formation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(formation, key, value)

    # Update slug if title changed
    if "title" in update_data:
        formation.slug = slugify.slugify(formation.title)

    # Auto-set is_full if max capacity reached
    if formation.max_participants and formation.current_participants >= formation.max_participants:
        formation.is_full = True
    else:
        formation.is_full = False

    # Update timestamp
    formation.updated_at = datetime.now()

    try:
        await db.commit()
        await db.refresh(formation)
        return formation
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


@formations_router.delete("/{formation_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_formation(
    formation_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a formation by slug
    """
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalar_one_or_none()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formation '{formation_slug}' non trouvée."
        )

    await db.delete(formation)
    await db.commit()
    return None


@formations_router.post("/{formation_slug}/register", status_code=status.HTTP_200_OK)
async def register_to_formation(
    formation_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a participant to a formation (increments current_participants)

    This is a simple counter increment. For full registration management,
    you would need a separate Participants/Registrations table.
    """
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalars().first()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formation non trouvée."
        )

    if formation.is_full:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formation complète. Aucune place disponible."
        )

    if formation.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formation déjà terminée."
        )

    # Increment participant count
    formation.current_participants += 1

    # Check if now full
    if formation.max_participants and formation.current_participants >= formation.max_participants:
        formation.is_full = True

    await db.commit()
    await db.refresh(formation)

    return {
        "message": "Inscription réussie",
        "formation": formation.title,
        "current_participants": formation.current_participants,
        "is_full": formation.is_full
    }
