"""
API Endpoints for Offre Projet Management
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
import os
from pathlib import Path
from uuid import UUID

from app.database.session import get_db
from app.models.offre_projet import OffreProjet
from app.models.users import User
from app.schemas.offre_projet import OffreProjetCreate, OffreProjetRead, OffreProjetUpdate
from app.core.auth import get_current_staff_user, get_current_redacteur_or_staff

offre_projet_router = APIRouter()

# Static directory for uploads
UPLOAD_DIR = Path("static/projets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@offre_projet_router.get("", response_model=List[OffreProjetRead])
async def get_all_projets(
    skip: int = 0,
    limit: int = 100,
    domaine: Optional[str] = None,
    statut: Optional[str] = None,
    ptf_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
) -> List[OffreProjet]:
    """Get all published projets with optional filters"""
    query = select(OffreProjet).options(selectinload(OffreProjet.ptf)).where(OffreProjet.statut_publication == "publie").offset(skip).limit(limit)
    if domaine:
        query = query.where(OffreProjet.domaine == domaine)
    if statut:
        query = query.where(OffreProjet.statut == statut)
    if ptf_id:
        query = query.where(OffreProjet.ptf_id == ptf_id)
    result = await db.execute(query)
    return result.scalars().all()


@offre_projet_router.get("/active", response_model=List[OffreProjetRead])
async def get_active_projets(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[OffreProjet]:
    """Get only active published projets (En cours)"""
    query = select(OffreProjet).options(selectinload(OffreProjet.ptf)).where(
        OffreProjet.statut == "En cours",
        OffreProjet.statut_publication == "publie"
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@offre_projet_router.get("/{slug}", response_model=OffreProjetRead)
async def get_projet_by_slug(slug: str, db: AsyncSession = Depends(get_db)) -> OffreProjet:
    """Get a single projet by slug"""
    query = select(OffreProjet).options(selectinload(OffreProjet.ptf)).where(OffreProjet.slug == slug)
    result = await db.execute(query)
    projet = result.scalar_one_or_none()
    if not projet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Projet with slug '{slug}' not found")
    return projet


@offre_projet_router.post("", response_model=OffreProjetRead, status_code=status.HTTP_201_CREATED)
async def create_projet(
    nom: str = Form(...),
    osc: str = Form(...),
    domaine: str = Form(...),
    zone: str = Form(...),
    durée: str = Form(...),
    budget: str = Form(...),
    objectif: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    beneficiaires: Optional[str] = Form(None),
    statut: str = Form("En attente"),
    progression: int = Form(0),
    resultats_attendus: Optional[str] = Form(None),
    partenaires: Optional[str] = Form(None),
    ptf_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_redacteur_or_staff),
) -> OffreProjet:
    """Create a new projet"""

    # Handle image upload
    image_filename = "default-project.jpg"
    if image and image.filename:
        file_extension = os.path.splitext(image.filename)[1]
        # Create a unique filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"projets/projet_{timestamp}{file_extension}"

        # Save the file
        file_path = UPLOAD_DIR.parent / image_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)

    statut_pub = "publie" if current_user.is_staff else "en_attente"

    # Create projet
    projet = OffreProjet(
        nom=nom,
        osc=osc,
        domaine=domaine,
        zone=zone,
        durée=durée,
        budget=budget,
        objectif=objectif,
        description=description,
        beneficiaires=beneficiaires,
        statut=statut,
        progression=progression,
        resultats_attendus=resultats_attendus,
        partenaires=partenaires,
        image_path=image_filename,
        statut_publication=statut_pub,
        ptf_id=ptf_id,
    )

    db.add(projet)
    await db.commit()
    await db.refresh(projet)

    return projet


@offre_projet_router.patch("/{slug}", response_model=OffreProjetRead)
async def update_projet(
    slug: str,
    nom: Optional[str] = Form(None),
    osc: Optional[str] = Form(None),
    domaine: Optional[str] = Form(None),
    zone: Optional[str] = Form(None),
    durée: Optional[str] = Form(None),
    budget: Optional[str] = Form(None),
    objectif: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    beneficiaires: Optional[str] = Form(None),
    statut: Optional[str] = Form(None),
    progression: Optional[int] = Form(None),
    resultats_attendus: Optional[str] = Form(None),
    partenaires: Optional[str] = Form(None),
    ptf_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
) -> OffreProjet:
    """Update an existing projet"""

    # Get existing projet
    query = select(OffreProjet).where(OffreProjet.slug == slug)
    result = await db.execute(query)
    projet = result.scalar_one_or_none()

    if not projet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projet with slug '{slug}' not found"
        )

    # Handle image upload
    if image and image.filename:
        # Delete old image if it exists and is not default
        if projet.image_path and projet.image_path != "default-project.jpg":
            old_image_path = UPLOAD_DIR.parent / projet.image_path
            if old_image_path.exists():
                old_image_path.unlink()

        # Save new image
        file_extension = os.path.splitext(image.filename)[1]
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"projets/projet_{timestamp}{file_extension}"

        file_path = UPLOAD_DIR.parent / image_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)

        projet.image_path = image_filename

    # Update fields
    if nom is not None:
        projet.nom = nom
        # Regenerate slug
        import slugify
        projet.slug = slugify.slugify(nom)
    if osc is not None:
        projet.osc = osc
    if domaine is not None:
        projet.domaine = domaine
    if zone is not None:
        projet.zone = zone
    if durée is not None:
        projet.durée = durée
    if budget is not None:
        projet.budget = budget
    if objectif is not None:
        projet.objectif = objectif
    if description is not None:
        projet.description = description
    if beneficiaires is not None:
        projet.beneficiaires = beneficiaires
    if statut is not None:
        projet.statut = statut
    if progression is not None:
        projet.progression = progression
    if resultats_attendus is not None:
        projet.resultats_attendus = resultats_attendus
    if partenaires is not None:
        projet.partenaires = partenaires
    if ptf_id is not None:
        projet.ptf_id = ptf_id

    await db.commit()

    # Re-query avec selectinload pour charger la relation ptf
    result2 = await db.execute(
        select(OffreProjet).options(selectinload(OffreProjet.ptf)).where(OffreProjet.id == projet.id)
    )
    return result2.scalar_one()


@offre_projet_router.get("/admin/en-attente", response_model=List[OffreProjetRead])
async def list_projets_en_attente(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Liste toutes les offres de projets en attente de validation (staff only)."""
    result = await db.execute(
        select(OffreProjet)
        .where(OffreProjet.statut_publication == "en_attente")
        .order_by(OffreProjet.created_at.asc())
    )
    return result.scalars().all()


@offre_projet_router.patch("/{slug}/valider", response_model=OffreProjetRead)
async def valider_projet(
    slug: str,
    action: str = Query(..., description="publie ou rejete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Approuver ou rejeter une offre de projet (staff only)."""
    if action not in ("publie", "rejete"):
        raise HTTPException(status_code=400, detail="Action invalide.")
    result = await db.execute(select(OffreProjet).where(OffreProjet.slug == slug))
    projet = result.scalar_one_or_none()
    if not projet:
        raise HTTPException(status_code=404, detail="Projet non trouvé.")
    projet.statut_publication = action
    await db.commit()
    await db.refresh(projet)
    return projet


@offre_projet_router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_projet(slug: str, db: AsyncSession = Depends(get_db)):
    """Delete a projet"""

    # Get projet
    query = select(OffreProjet).where(OffreProjet.slug == slug)
    result = await db.execute(query)
    projet = result.scalar_one_or_none()

    if not projet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projet with slug '{slug}' not found"
        )

    # Delete image file if it exists and is not default
    if projet.image_path and projet.image_path != "default-project.jpg":
        image_path = UPLOAD_DIR.parent / projet.image_path
        if image_path.exists():
            image_path.unlink()

    # Delete from database
    await db.delete(projet)
    await db.commit()

    return None
