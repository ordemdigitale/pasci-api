import os, uuid, slugify
from fastapi import APIRouter, HTTPException, UploadFile, status,  Depends, Form, File, Query
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List
from app.core.config import settings
from app.database.session import get_db
from app.core.auth import get_current_superuser
from app.models.users import User
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

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]

async def _save_upload(file: UploadFile, field: str) -> str:
    """Lit et sauvegarde un UploadFile de manière async. Retourne le nom de fichier."""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"type": "validation_error", "errors": [
                {"field": field, "message": f"Format invalide. Formats acceptés : {ALLOWED_IMAGE_EXTENSIONS}."}
            ]}
        )
    contents = await file.read()
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    return filename

def _delete_file(path: Optional[str]) -> None:
    """Supprime un fichier uploadé si il existe."""
    if path and path != "default.png":
        full_path = os.path.join(settings.UPLOAD_DIR, path)
        if os.path.exists(full_path):
            os.remove(full_path)

######################
# PTF Endpoints
######################
# create: POST
@ptf_router.post("", response_model=PtfRead, status_code=status.HTTP_201_CREATED)
async def create_ptf(
  name: str = Form(...),
  description: Optional[str] = Form(None),
  mission: Optional[str] = Form(None),
  vision: Optional[str] = Form(None),
  website: Optional[str] = Form(None),
  email: Optional[str] = Form(None),
  phone: Optional[str] = Form(None),
  address: Optional[str] = Form(None),
  pays: Optional[str] = Form(None),
  date_creation: Optional[str] = Form(None),
  categorie: Optional[str] = Form(None),
  exigences_majeures: Optional[str] = Form(None),
  nature_relations: Optional[str] = Form(None),
  domaines: Optional[str] = Form(None),
  thumbnail: Optional[UploadFile] = File(None),
  cover: Optional[UploadFile] = File(None),
  db: AsyncSession = Depends(get_db),
  current_user: User = Depends(get_current_superuser),
) -> Ptf:

  # Check for duplicate PTF name first (before saving files)
  result = await db.execute(select(Ptf).where(Ptf.name == name))
  if result.scalars().first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [{"field": "name", "message": "Un PTF avec ce nom existe déjà. Veuillez choisir un nom différent."}]
      }
    )

  try:
    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
      thumbnail_saved_path = await _save_upload(thumbnail, "thumbnail")
    else:
      thumbnail_saved_path = "default.png"

    # Handle cover image upload
    cover_saved_path = None
    if cover and cover.filename:
      cover_saved_path = await _save_upload(cover, "cover")

    db_ptf = Ptf(
      name=name,
      description=description,
      mission=mission,
      vision=vision,
      thumbnail_path=thumbnail_saved_path,
      cover_path=cover_saved_path,
      website=website,
      email=email,
      phone=phone,
      address=address,
      pays=pays,
      date_creation=date_creation,
      categorie=categorie,
      exigences_majeures=exigences_majeures,
      nature_relations=nature_relations,
      domaines=domaines,
    )
    db.add(db_ptf)
    await db.commit()
    await db.refresh(db_ptf)
    return db_ptf
  except HTTPException:
    raise
  except Exception as e:
    await db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail={
        "type": "database_error",
        "errors": [{"field": "database", "message": f"Erreur lors de la création: {str(e)}"}]
      }
    )

# read: GET
## read all
@ptf_router.get("", response_model=List[PtfReadWithProjets], status_code=status.HTTP_200_OK)
async def get_ptfs(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """Get all PTF with pagination"""
    result = await db.execute(
        select(Ptf)
        .options(selectinload(Ptf.projets))
        .offset(skip)
        .limit(limit)
        .order_by(Ptf.name)
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
  if not ptf:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PTF non trouvé.")
  return ptf

## update: PATCH
@ptf_router.patch("/{ptf_slug}", response_model=PtfReadWithProjets, status_code=status.HTTP_200_OK)
async def update_ptf(
  ptf_slug: str,
  name: Optional[str] = Form(None),
  description: Optional[str] = Form(None),
  mission: Optional[str] = Form(None),
  vision: Optional[str] = Form(None),
  website: Optional[str] = Form(None),
  email: Optional[str] = Form(None),
  phone: Optional[str] = Form(None),
  address: Optional[str] = Form(None),
  pays: Optional[str] = Form(None),
  date_creation: Optional[str] = Form(None),
  categorie: Optional[str] = Form(None),
  exigences_majeures: Optional[str] = Form(None),
  nature_relations: Optional[str] = Form(None),
  domaines: Optional[str] = Form(None),
  thumbnail: Optional[UploadFile] = File(None),
  cover: Optional[UploadFile] = File(None),
  remove_thumbnail: Optional[str] = Form(None),
  remove_cover: Optional[str] = Form(None),
  db: AsyncSession = Depends(get_db),
  current_user: User = Depends(get_current_superuser),
):
  """Update a PTF by slug"""
  # Fetch existing PTF
  result = await db.execute(
    select(Ptf).where(Ptf.slug == ptf_slug).options(selectinload(Ptf.projets))
  )
  ptf = result.scalars().first()
  if not ptf:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="PTF non trouvé."
    )

  # Handle thumbnail
  if thumbnail and getattr(thumbnail, 'filename', None):
    _delete_file(ptf.thumbnail_path)
    ptf.thumbnail_path = await _save_upload(thumbnail, "thumbnail")
  elif remove_thumbnail == "1":
    _delete_file(ptf.thumbnail_path)
    ptf.thumbnail_path = None

  # Handle cover
  if cover and getattr(cover, 'filename', None):
    _delete_file(ptf.cover_path)
    ptf.cover_path = await _save_upload(cover, "cover")
  elif remove_cover == "1":
    _delete_file(ptf.cover_path)
    ptf.cover_path = None

  # Update text fields only if provided
  if name is not None:
    ptf.name = name
    ptf.slug = slugify.slugify(name)
  if description is not None:
    ptf.description = description
  if mission is not None:
    ptf.mission = mission
  if vision is not None:
    ptf.vision = vision
  if website is not None:
    ptf.website = website
  if email is not None:
    ptf.email = email
  if phone is not None:
    ptf.phone = phone
  if address is not None:
    ptf.address = address
  if pays is not None:
    ptf.pays = pays
  if date_creation is not None:
    ptf.date_creation = date_creation
  if categorie is not None:
    ptf.categorie = categorie
  if exigences_majeures is not None:
    ptf.exigences_majeures = exigences_majeures
  if nature_relations is not None:
    ptf.nature_relations = nature_relations
  if domaines is not None:
    ptf.domaines = domaines

  # Persist changes
  await db.commit()

  # Re-requêter avec selectinload pour charger les relations (refresh seul ne les recharge pas en async)
  result = await db.execute(
    select(Ptf).options(selectinload(Ptf.projets)).where(Ptf.id == ptf.id)
  )
  return result.scalars().first()

## delete: DELETE
@ptf_router.delete("/{ptf_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ptf(ptf_slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_superuser)):
  """Delete a PTF by slug"""
  # Find PTF by slug
  result = await db.execute(select(Ptf).where(Ptf.slug == ptf_slug))
  ptf = result.scalar_one_or_none()

  # Raise 404 if PTF does not exist
  if not ptf:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"PTF {ptf_slug} non trouvé."
    )

  # Delete associated files if they exist
  if ptf.thumbnail_path and ptf.thumbnail_path != "default.png":
    thumbnail_file_path = os.path.join(settings.UPLOAD_DIR, ptf.thumbnail_path)
    if os.path.exists(thumbnail_file_path):
      os.remove(thumbnail_file_path)

  if ptf.cover_path:
    cover_file_path = os.path.join(settings.UPLOAD_DIR, ptf.cover_path)
    if os.path.exists(cover_file_path):
      os.remove(cover_file_path)

  # Delete the PTF from database
  await db.delete(ptf)
  await db.commit()
  return None

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