from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from app.database.session import get_db
from app.models.jobs import Jobs
from app.schemas.jobs import JobsCreate, JobsRead, JobsUpdate
import slugify

jobs_router = APIRouter()

@jobs_router.post("", response_model=JobsRead, status_code=status.HTTP_201_CREATED)
async def create_job(job: JobsCreate, db: AsyncSession = Depends(get_db)) -> Jobs:
  db_job = Jobs(**job.model_dump())
  db.add(db_job)
  await db.commit()
  await db.refresh(db_job)
  return db_job


@jobs_router.get("", response_model=List[JobsRead], status_code=status.HTTP_200_OK)
async def get_jobs(db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Jobs).order_by(desc(Jobs.publication_date)))
  jobs = result.scalars().all()
  return jobs


# Get jobs where is_expired is false
@jobs_router.get("/active", response_model=List[JobsRead], status_code=status.HTTP_200_OK)
async def get_active_jobs(db: AsyncSession = Depends(get_db)):
  result = await db.execute(
    select(Jobs).where(Jobs.is_expired == False).order_by(desc(Jobs.publication_date))
  )
  jobs = result.scalars().all()
  return jobs


@jobs_router.get("/{job_slug}", response_model=JobsRead, status_code=status.HTTP_200_OK)
async def get_single_job(job_slug: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
  job = result.scalars().first()
  if not job:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre d'emploi non trouvé.")

  return job

#update
@jobs_router.patch("/{job_slug}", response_model=JobsRead, status_code=status.HTTP_200_OK)
async def update_job(job_slug: str, job_update: JobsUpdate, db: AsyncSession = Depends(get_db)):
  # fetch existing resource by slug
  result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
  job = result.scalars().first()
  if not job:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre d'emploi non trouvée.")
  # extract fields provided in the request (exclude unset ones)
  update_data = job_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(job, key, value)
  # update slug if name changed
  if "title" in update_data:
     job.slug = slugify.slugify(job.title)

  # persist changes
  await db.commit()
  await db.refresh(job)
  return job


#delete
@jobs_router.delete("/{job_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_slug: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Jobs).where(Jobs.slug == job_slug))
  job = result.scalar_one_or_none()
  # raise 404 if not exist
  if not job:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Offre d'emploi non trouvé."
    )
  await db.delete(job)
  await db.commit()
  return None