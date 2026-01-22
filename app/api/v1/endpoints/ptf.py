import os, shutil, uuid, slugify
from fastapi import APIRouter, HTTPException, UploadFile, status,  Depends, Form, File
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List
from app.core.config import settings
from app.database.session import get_db
from app.schemas.ptf import(
  PtfCreate,
  PtfRead,
  PtfReadWithProjets,
  PtfUpdate,
  ProjetCreate,
  ProjetRead,
  ProjetReadWithPtf,
  ProjetUpdate
)
from app.models.ptf import Ptf, Projet

ptf_router = APIRouter()

######################
# PTF Endpoints
######################
# create: POST
@ptf_router.post("", response_model=PtfRead, status_code=status.HTTP_201_CREATED)
async def create_ptf(
  name: str = Form(...),
  description: Optional[str] = Form(None),  
  thumbnail: Optional[UploadFile] = File(None),
  db: AsyncSession = Depends(get_db)
) -> Ptf:
  
  if thumbnail and thumbnail.filename:
    # User uploaded image: generate unique name and save
    file_extension = thumbnail.filename.split(".")[-1]
    # check for the extension to ensure users only upload images
    allowed_extensions = ["jpg", "jpeg", "png", "webp"]
    if file_extension.lower() not in allowed_extensions:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
          "type": "validation_error",
          "errors": [
            {
              "field": "thumbnail",
              "message": f"Format d'image invalide. Les formats valides sont: {allowed_extensions}."
            }
          ]
        }
      )
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
      shutil.copyfileobj(thumbnail.file, buffer)

    saved_path = filename
  else:
    # No file uploaded, use the default filename defined in your model
    saved_path = "default.png"

  # create the db record
  ptf_create = Ptf(
    name=name,
    description=description,
    thumbnail_path=saved_path,
  )

  # Check for duplicate PTF name
  result = await db.execute(select(Ptf).where(Ptf.name == ptf_create.name))
  existing_news = result.scalars().first()
  if existing_news:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [
          {
            "field": "name",
            "message": "Un PTF avec ce nom existe déjà. Veuillez choisir un nom différent."
          }
        ]
      }
    )
  
  try:
    db_ptf = Ptf(**ptf_create.model_dump())
    db.add(db_ptf)
    await db.commit()
    await db.refresh(db_ptf)
    return db_ptf
  except Exception as e:
    await db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail={
        "type": "database_error",
        "errors": [
          {
            "field": "database",
            "message": f"Erreur lors de la création: {str(e)}"
          }
        ]
      }
    )

# read: GET
## read all
@ptf_router.get("", response_model=List[PtfReadWithProjets], status_code=status.HTTP_200_OK)
async def get_ptfs(db: AsyncSession = Depends(get_db)):
  result = await db.execute(
    select(Ptf).options(selectinload(Ptf.projets))
  )
  ptfs = result.scalars().all()
  return ptfs
### read single
@ptf_router.get("/{ptf_slug}", response_model=PtfReadWithProjets, status_code=status.HTTP_200_OK)
async def get_ptf(ptf_slug: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(
    select(Ptf).options(selectinload(Ptf.projets)).where(Ptf.slug == ptf_slug)
  )
  ptf = result.scalars().first()
  return ptf

## update: PATCH
#@ptf_router.patch("/teams/{team_slug}", response_model=TeamReadWithHeroes, status_code=status.HTTP_200_OK)
#async def update_team(team_slug: str, team_update: TeamUpdate, db: AsyncSession = Depends(get_db)):
#  # fetch existing resource by slug
#  result = await db.execute(
#    select(Team).where(Team.slug == team_slug).options(selectinload(Team.heroes))
#  )
#  team = result.scalars().first()
#  if not team:
#    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team non trouvée.")
#  # extract fields provided in the request (exclude unset ones)
#  update_data = team_update.model_dump(exclude_unset=True)
#  # update the database object attributes
#  for key, value in update_data.items():
#    setattr(team, key, value)
#  # update slug if name changed
#  if "name" in update_data:
#     team.slug = slugify.slugify(team.name)
#
#  # persist changes
#  await db.commit()
#  await db.refresh(team)
#  return team
#
## delete: DELETE
#@ptf_router.delete("/teams/{team_slug}", status_code=status.HTTP_204_NO_CONTENT)
#async def delete_team(team_slug: str, db: AsyncSession = Depends(get_db)):
#  """ Delete a Team """
#  # find team by slug
#  result = await db.execute(select(Team).where(Team.slug == team_slug))
#  team = result.scalar_one_or_none()
#  # raise 404 if team does not exist
#  if not team:
#    raise HTTPException(
#      status_code=status.HTTP_404_NOT_FOUND,
#      detail=f"Team {team_slug} not found."
#    )
#  await db.delete(team)
#  await db.commit()
#  return None
#
#######################
## Hero Endpoints
#######################
## create: POST
#@ptf_router.post("/hero", response_model=HeroRead, status_code=status.HTTP_201_CREATED)
#async def create_hero(
#  name: str = Form(...),
#  team_id: str = Form(""),
#  db: AsyncSession = Depends(get_db)
#):
#  # convert empty strings to None
#  team_id_int = int(team_id) if team_id and team_id != "" else None
#  # create the db record
#  hero_create = Hero(
#    name=name,
#    team_id=team_id_int
#  )
#  # check for duplicate hero name
#  result = await db.execute(select(Hero).where(Hero.name == hero_create.name))
#  existing_hero = result.scalars().first()
#  if existing_hero:
#    raise HTTPException(
#      status_code=status.HTTP_409_CONFLICT,
#      detail={
#        "type": "duplicate_error",
#        "errors": [
#          {
#            "field": "name",
#            "message": f"le héro {existing_hero.name} existe déjà. Veuillez choisir un nom différent."
#          }
#        ]
#      }
#    )
#  try:
#    db_hero = Hero(**hero_create.model_dump())
#    db.add(db_hero)
#    await db.commit()
#    await db.refresh(db_hero)
#    return db_hero
#  except Exception as e:
#    await db.rollback()
#    raise HTTPException(
#      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#      detail={
#        "type": "database_error",
#        "errors": [
#          {
#            "field": "database",
#            "message": f"Erreur lors de la création du héro: {str(e)}"
#          }
#        ]
#      }
#    )
#
## read: GET
### read all
#@ptf_router.get("/heroes", response_model=list[HeroReadWithTeam], status_code=status.HTTP_200_OK)
#async def get_heroes(db: AsyncSession = Depends(get_db)):
#  result = await db.execute(
#    select(Hero).options(joinedload(Hero.team))
#  )
#  heroes = result.scalars().all()
#  return heroes
#
### read single
#@ptf_router.get("/heroes/{team_slug}", response_model=list[TeamReadWithHeroes], status_code=status.HTTP_200_OK)
#async def get_hero(team_slug: str, db: AsyncSession = Depends(get_db)):
#  #result = await db.execute(select(RegionCiv).order_by(desc(RegionCiv.name)))
#  result = await db.execute(
#    select(Team).options(selectinload(Team.heroes)).where(Team.slug == team_slug)
#  )
#  team = result.scalars().all()
#  return team
#
## update: PATCH
#@ptf_router.patch("/heroes/{team_slug}", response_model=TeamReadWithHeroes, status_code=status.HTTP_200_OK)
#async def update_hero(team_slug: str, team_update: TeamUpdate, db: AsyncSession = Depends(get_db)):
#  # fetch existing resource by slug
#  result = await db.execute(
#    select(Team).where(Team.slug == team_slug).options(selectinload(Team.heroes))
#  )
#  team = result.scalars().first()
#  if not team:
#    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team non trouvée.")
#  # extract fields provided in the request (exclude unset ones)
#  update_data = team_update.model_dump(exclude_unset=True)
#  # update the database object attributes
#  for key, value in update_data.items():
#    setattr(team, key, value)
#  # update slug if name changed
#  if "name" in update_data:
#     team.slug = slugify.slugify(team.name)
#
#  # persist changes
#  await db.commit()
#  await db.refresh(team)
#  return team
#
## delete: DELETE
#@ptf_router.delete("/heroes/{team_slug}", status_code=status.HTTP_204_NO_CONTENT)
#async def delete_hero(team_slug: str, db: AsyncSession = Depends(get_db)):
#  """ Delete a Team """
#  # find team by slug
#  result = await db.execute(select(Team).where(Team.slug == team_slug))
#  team = result.scalar_one_or_none()
#  # raise 404 if team does not exist
#  if not team:
#    raise HTTPException(
#      status_code=status.HTTP_404_NOT_FOUND,
#      detail=f"Team {team_slug} not found."
#    )
#  await db.delete(team)
#  await db.commit()
#  return None