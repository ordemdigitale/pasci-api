from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from app.database.session import get_db
from app.models.jobs import Jobs
from app.schemas.jobs import JobsCreate, JobsRead

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