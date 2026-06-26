from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from app.database.session import get_db
from app.models.jobs import Jobs
from app.models.users import User
from app.schemas.jobs import JobsCreate, JobsRead, JobsUpdate
from app.core.auth import get_current_staff_user, get_current_redacteur_or_staff, get_optional_current_user
import slugify

jobs_router = APIRouter()

@jobs_router.post("", response_model=JobsRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job: JobsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_redacteur_or_staff),
) -> Jobs:
    statut = "publie" if current_user.is_staff else "en_attente"
    db_job = Jobs(**job.model_dump(), statut_publication=statut)
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    return db_job


@jobs_router.get("", response_model=List[JobsRead], status_code=status.HTTP_200_OK)
async def get_jobs(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """Get all published jobs with pagination"""
    result = await db.execute(
        select(Jobs)
        .where(Jobs.statut_publication == "publie")
        .order_by(desc(Jobs.publication_date))
        .offset(skip)
        .limit(limit)
    )
    jobs = result.scalars().all()
    return jobs


@jobs_router.get("/active", response_model=List[JobsRead], status_code=status.HTTP_200_OK)
async def get_active_jobs(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """Get all active (non-expired) published jobs with pagination"""
    result = await db.execute(
        select(Jobs)
        .where(Jobs.is_expired == False, Jobs.statut_publication == "publie")
        .order_by(desc(Jobs.publication_date))
        .offset(skip)
        .limit(limit)
    )
    jobs = result.scalars().all()
    return jobs


@jobs_router.get("/admin/en-attente", response_model=List[JobsRead])
async def list_jobs_en_attente(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Liste toutes les offres d'emploi en attente de validation (staff only)."""
    query = select(Jobs).where(Jobs.statut_publication == "en_attente").order_by(Jobs.created_at.asc())
    result = await db.execute(query)
    return result.scalars().all()


@jobs_router.patch("/{job_slug}/valider", response_model=JobsRead)
async def valider_job(
    job_slug: str,
    action: str = Query(..., description="publie ou rejete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Approuver ou rejeter une offre d'emploi (staff only)."""
    if action not in ("publie", "rejete"):
        raise HTTPException(status_code=400, detail="Action invalide. Utilisez 'publie' ou 'rejete'.")
    result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Offre d'emploi non trouvée.")
    job.statut_publication = action
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


@jobs_router.get("/{job_slug}", response_model=JobsRead, status_code=status.HTTP_200_OK)
async def get_single_job(
    job_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre d'emploi non trouvé.")
    if job.statut_publication != "publie" and not (
        current_user and (current_user.is_staff or current_user.is_superuser)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre d'emploi non trouvé.")
    return job


@jobs_router.patch("/{job_slug}", response_model=JobsRead, status_code=status.HTTP_200_OK)
async def update_job(
    job_slug: str,
    job_update: JobsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre d'emploi non trouvée.")
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    if "title" in update_data:
        job.slug = slugify.slugify(job.title)
    await db.commit()
    await db.refresh(job)
    return job


@jobs_router.delete("/{job_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre d'emploi non trouvé.")
    await db.delete(job)
    await db.commit()
    return None
