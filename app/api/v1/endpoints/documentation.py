# app/api/v1/endpoints/documentation.py | Documentation endpoints
import os
import uuid
from datetime import datetime
from typing import Optional, List

import slugify
from fastapi import APIRouter, HTTPException, status, UploadFile, Depends, File, Form, Query
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy.orm import selectinload
from sqlmodel import desc, select, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.schemas.documentation import (
    DocumentationRead,
    DocumentationReadDetail,
    DocumentationUpdate
)
from app.models.documentation import Documentation

documentation_router = APIRouter()

# Configuration for file uploads
ALLOWED_DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"]
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB for documents
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB for images
THUMBNAIL_SIZE = (800, 600)  # Max dimensions for thumbnails

# Create documents directory if it doesn't exist
DOCUMENTS_DIR = os.path.join(settings.UPLOAD_DIR, "documents")
if not os.path.exists(DOCUMENTS_DIR):
    os.makedirs(DOCUMENTS_DIR)


def validate_and_process_document(file: UploadFile) -> tuple[str, str, int]:
    """
    Validate and save uploaded document
    Returns (filename, file_type, file_size)
    Raises HTTPException if validation fails
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "file",
                    "message": "Aucun fichier fourni."
                }]
            }
        )

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "file",
                    "message": f"Format de fichier invalide. Formats acceptés: {', '.join(ALLOWED_DOCUMENT_EXTENSIONS)}."
                }]
            }
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_DOCUMENT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "file",
                    "message": f"Fichier trop volumineux. Taille maximale: {MAX_DOCUMENT_SIZE // (1024*1024)}MB."
                }]
            }
        )

    # Generate unique filename
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(DOCUMENTS_DIR, filename)

    # Save file
    try:
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
        return filename, file_extension, file_size
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "processing_error",
                "errors": [{
                    "field": "file",
                    "message": f"Erreur lors de l'enregistrement du fichier: {str(e)}"
                }]
            }
        )


def validate_and_process_image(file: UploadFile) -> str:
    """
    Validate and process uploaded image
    Returns the saved filename
    Raises HTTPException if validation fails
    """
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
    if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "thumbnail",
                    "message": f"Format d'image invalide. Formats acceptés: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}."
                }]
            }
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "thumbnail",
                    "message": f"Fichier trop volumineux. Taille maximale: {MAX_IMAGE_SIZE // (1024*1024)}MB."
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


@documentation_router.post("", response_model=DocumentationRead, status_code=status.HTTP_201_CREATED)
async def create_documentation(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    type: str = Form("documentation"),
    category: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    thumbnail: Optional[UploadFile] = File(None),
    crasc_id: str = Form(""),
    osc_id: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new documentation entry

    - **title**: Title of the document (required)
    - **description**: Description of the document
    - **type**: Type of resource ('documentation' or 'fiche')
    - **category**: Category (Rapport, Guide, Étude, Manuel, PV, Infographie, Politique, Récit, Plan)
    - **file**: Document file (PDF, DOCX, etc., optional, max 50MB)
    - **thumbnail**: Cover image (optional, max 5MB)
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

    # Handle document file upload
    file_path = None
    file_type = None
    file_size = None
    if file and file.filename:
        saved_filename, file_ext, file_sz = validate_and_process_document(file)
        # Store relative path for static file serving
        file_path = f"documents/{saved_filename}"
        file_type = file_ext
        file_size = file_sz

    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
        saved_path = validate_and_process_image(thumbnail)
    else:
        saved_path = "default.png"

    # Create database record
    doc_create = Documentation(
        title=title.strip(),
        description=description,
        type=type,
        category=category,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        crasc_id=crasc_id_int,
        osc_id=osc_id_int,
        thumbnail_path=saved_path
    )

    # Check for duplicate title
    result = await db.execute(select(Documentation).where(Documentation.title == doc_create.title))
    existing_doc = result.scalars().first()
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "duplicate_error",
                "errors": [{
                    "field": "title",
                    "message": "Un document avec ce titre existe déjà."
                }]
            }
        )

    try:
        db.add(doc_create)
        await db.commit()
        await db.refresh(doc_create)
        return doc_create
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


@documentation_router.get("", response_model=List[DocumentationReadDetail], status_code=status.HTTP_200_OK)
async def get_all_documentation(
    skip: int = Query(0, ge=0, description="Nombre de documents à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre de documents à retourner"),
    type: Optional[str] = Query(None, description="Filtrer par type ('documentation' ou 'fiche')"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    crasc_id: Optional[int] = Query(None, description="Filtrer par CRASC ID"),
    osc_id: Optional[int] = Query(None, description="Filtrer par OSC ID"),
    search: Optional[str] = Query(None, description="Rechercher dans titre/description"),
    sort_by: str = Query("created_at", description="Champ de tri (created_at, title)"),
    sort_order: str = Query("desc", description="Ordre de tri (asc, desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all documentation entries with filtering and pagination

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max 100)
    - **type**: Filter by type ('documentation' or 'fiche')
    - **category**: Filter by category
    - **crasc_id**: Filter by CRASC
    - **osc_id**: Filter by OSC
    - **search**: Search in title and description
    - **sort_by**: Sort field (created_at, title)
    - **sort_order**: Sort order (asc, desc)
    """
    # Base query with relationships
    query = select(Documentation).options(
        selectinload(Documentation.crasc),
        selectinload(Documentation.osc)
    )

    # Apply filters
    if type:
        query = query.where(Documentation.type == type)

    if category:
        query = query.where(Documentation.category == category)

    if crasc_id:
        query = query.where(Documentation.crasc_id == crasc_id)

    if osc_id:
        query = query.where(Documentation.osc_id == osc_id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Documentation.title.ilike(search_term),
                Documentation.description.ilike(search_term)
            )
        )

    # Apply sorting
    if sort_by == "title":
        order_column = Documentation.title
    else:  # default to created_at
        order_column = Documentation.created_at

    if sort_order == "asc":
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    docs_list = result.scalars().all()

    return docs_list


@documentation_router.get("/categories", response_model=List[str], status_code=status.HTTP_200_OK)
async def get_categories(db: AsyncSession = Depends(get_db)):
    """
    Get all unique categories from documentation
    """
    query = select(Documentation.category).distinct().where(Documentation.category.is_not(None))
    result = await db.execute(query)
    categories = [cat for cat in result.scalars().all() if cat]
    return sorted(categories)


@documentation_router.get("/{doc_slug}", response_model=DocumentationReadDetail, status_code=status.HTTP_200_OK)
async def get_single_documentation(
    doc_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single documentation entry by slug
    """
    query = select(Documentation).where(Documentation.slug == doc_slug).options(
        selectinload(Documentation.crasc),
        selectinload(Documentation.osc)
    )

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé."
        )

    return doc


async def get_documentation_update_form(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    crasc_id: str = Form(""),
    osc_id: str = Form("")
) -> DocumentationUpdate:
    """Parse form data into DocumentationUpdate"""
    update_dict = {}

    if title is not None:
        update_dict["title"] = title

    if description is not None:
        update_dict["description"] = description

    if type is not None:
        update_dict["type"] = type

    if category is not None:
        update_dict["category"] = category

    # Parse IDs - only include if provided
    if crasc_id and crasc_id != "":
        update_dict["crasc_id"] = int(crasc_id)

    if osc_id and osc_id != "":
        update_dict["osc_id"] = int(osc_id)

    return DocumentationUpdate(**update_dict)


@documentation_router.patch("/{doc_slug}", response_model=DocumentationReadDetail, status_code=status.HTTP_200_OK)
async def update_documentation(
    doc_slug: str,
    doc_update: DocumentationUpdate = Depends(get_documentation_update_form),
    file: Optional[UploadFile] = File(None),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a documentation entry

    - **title**: New title (optional)
    - **description**: New description (optional)
    - **category**: New category (optional)
    - **file**: New document file (optional)
    - **thumbnail**: New cover image (optional)
    - **crasc_id**: New CRASC association (optional)
    - **osc_id**: New OSC association (optional)
    """
    # Fetch existing documentation
    result = await db.execute(
        select(Documentation).where(Documentation.slug == doc_slug).options(
            selectinload(Documentation.crasc),
            selectinload(Documentation.osc)
        )
    )
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé."
        )

    # Handle document file upload
    if file and file.filename:
        # Delete old file if exists
        if doc.file_path:
            old_file_path = os.path.join(settings.UPLOAD_DIR, doc.file_path)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception:
                    pass  # Ignore errors when deleting old file
        
        saved_filename, file_ext, file_sz = validate_and_process_document(file)
        doc.file_path = f"documents/{saved_filename}"
        doc.file_type = file_ext
        doc.file_size = file_sz

    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
        # Delete old thumbnail if exists and not default
        if doc.thumbnail_path and doc.thumbnail_path != "default.png":
            old_thumb_path = os.path.join(settings.UPLOAD_DIR, doc.thumbnail_path)
            if os.path.exists(old_thumb_path):
                try:
                    os.remove(old_thumb_path)
                except Exception:
                    pass  # Ignore errors when deleting old thumbnail
        
        saved_path = validate_and_process_image(thumbnail)
        doc.thumbnail_path = saved_path

    # Update other fields (only fields that were provided in the form)
    update_data = doc_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)

    # Update slug if title changed
    if "title" in update_data:
        doc.slug = slugify.slugify(doc.title)

    # Update timestamp
    doc.updated_at = datetime.now()

    try:
        await db.commit()
        await db.refresh(doc)
        return doc
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


@documentation_router.get("/{doc_slug}/download")
async def download_documentation(
    doc_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download a documentation file

    Returns the file as a downloadable attachment
    """
    # Fetch the documentation
    result = await db.execute(
        select(Documentation).where(Documentation.slug == doc_slug)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé."
        )

    if not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce document n'a pas de fichier associé."
        )

    # Construct the full file path
    file_path = os.path.join(settings.UPLOAD_DIR, doc.file_path)

    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Le fichier n'existe pas sur le serveur. Chemin: {doc.file_path}"
        )

    # Get the original filename from the title and extension
    filename = f"{doc.title}.{doc.file_type}" if doc.file_type else doc.title

    # Return the file as a download
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@documentation_router.delete("/{doc_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_documentation(doc_slug: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a documentation entry by slug
    Also deletes associated files
    """
    result = await db.execute(select(Documentation).where(Documentation.slug == doc_slug))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_slug}' non trouvé."
        )

    # Delete associated files
    if doc.file_path:
        file_path = os.path.join(settings.UPLOAD_DIR, doc.file_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # Ignore errors when deleting file

    if doc.thumbnail_path and doc.thumbnail_path != "default.png":
        thumb_path = os.path.join(settings.UPLOAD_DIR, doc.thumbnail_path)
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass  # Ignore errors when deleting thumbnail

    await db.delete(doc)
    await db.commit()
    return None
