import os, shutil, uuid
from fastapi import APIRouter, HTTPException, status, UploadFile, Depends, File, Form, Request
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Annotated

from app.core.config import settings
from app.database.session import get_db
from app.schemas.crasc import (
  RegionCivCreate,
  RegionCivRead,
  RegionCivReadWithCrascRegion,
  OscTypeBase,
  OscTypeCreate,
  OscTypeRead,
  OscTypeReadWithOscs,
  OscTypeUpdate,
  OscCreate,
  OscRead,
  OscReadWithCrascRegionAndOscType,
  OscReadWithOscType,
  OscReadWithCrascRegion,
  CrascRegionBase,
  CrascRegionCreate,
  CrascRegionRead,
  CrascRegionReadWithOscs,
  CrascRegionReadWithOscsAndRegionCivs,
  CrascRegionUpdate,
  NewsArticleCreate,
  NewsArticleRead,
  NewsArticleReadWithOsc,
  NewsCreate,
  NewsRead,
  NewsReadWithCrascAndOsc
)
from app.models.crasc import RegionCiv, CrascRegion, OscType, Osc, NewsArticles, News

crasc_router = APIRouter()

######################
# RegionCivs Endpoints
######################

#@crasc_router.post("/region-civ", response_model=RegionCiv, status_code=status.HTTP_201_CREATED)
#async def create_region_civ(region_civ: RegionCiv, db: AsyncSession = Depends(get_db)) -> RegionCiv:
#    db_region_civ = RegionCiv(**region_civ.model_dump())
#    db.add(db_region_civ)
#    await db.commit()
#    await db.refresh(db_region_civ)
#    return db_region_civ

# Create RegionCiv (check for duplicate region civ name) and assign to CrascRegion
@crasc_router.post("/region-civ-with-crasc", response_model=RegionCivRead, status_code=status.HTTP_201_CREATED)
async def create_region_civ_with_crasc(region_civ: RegionCivCreate, db: AsyncSession = Depends(get_db)) -> RegionCiv:
  # Check for duplicate name
  result = await db.execute(select(RegionCiv).where(RegionCiv.name == region_civ.name))
  existing_region_civ = result.scalars().first()
  if existing_region_civ:
    raise HTTPException(status_code=400, detail="Cette région de la Côte d'Ivoire existe déjà.")
  # Validate that the crasc_region_id exists
  result = await db.execute(select(CrascRegion).where(CrascRegion.id == region_civ.crasc_region_id))
  crasc_region = result.scalar_one_or_none()
  if not crasc_region:
    raise HTTPException(status_code=400, detail="La région CRASC spécifiée n'existe pas.")
  
  db_region_civ = RegionCiv(**region_civ.model_dump())
  db.add(db_region_civ)
  await db.commit()
  await db.refresh(db_region_civ)
  return db_region_civ

@crasc_router.get("/region-civ", response_model=list[RegionCivReadWithCrascRegion], status_code=status.HTTP_200_OK)
async def get_region_civs(db: AsyncSession = Depends(get_db)):
    #result = await db.execute(select(RegionCiv).order_by(desc(RegionCiv.name)))
    result = await db.execute(
        select(RegionCiv).options(joinedload(RegionCiv.crasc_region))
    )
    region_civs = result.scalars().all()
    return region_civs

######################
# CrascRegion Endpoints
######################
@crasc_router.post("/region-crasc", response_model=CrascRegionRead, status_code=status.HTTP_201_CREATED)
async def create_crasc_region(crasc_region: CrascRegionCreate, db: AsyncSession = Depends(get_db)) -> CrascRegion:
    # Check for duplicate name
    result = await db.execute(select(CrascRegion).where(CrascRegion.name == crasc_region.name))
    existing_crasc_region = result.scalars().first()
    if existing_crasc_region:
      raise HTTPException(status_code=400, detail="Cette région CRASC existe déjà.")
    db_crasc_region = CrascRegion(**crasc_region.model_dump())
    db.add(db_crasc_region)
    await db.commit()
    await db.refresh(db_crasc_region)
    return db_crasc_region

@crasc_router.get("/region-crasc", response_model=list[CrascRegionRead], status_code=status.HTTP_200_OK)
async def get_crasc_regions(db: AsyncSession = Depends(get_db)):
    """ Get all CRASC regions. """

    result = await db.execute(select(CrascRegion).order_by(desc(CrascRegion.name)))
    crasc_regions = result.scalars().all()
    return crasc_regions

#@crasc_router.get("/region-crasc/{region_id}", response_model=CrascRegionReadWithOscs, status_code=status.HTTP_200_OK)
#async def get_crasc_region_with_oscs(region_id: int, db: AsyncSession = Depends(get_db)):
#  result = await db.execute(
#      select(CrascRegion).options(selectinload(CrascRegion.oscs)).where(CrascRegion.id == region_id)
#  )
#  region = result.scalars().first()
#  if not region:
#    raise HTTPException(status_code=404, detail="Region CRASC non trouvé.")
#  return region

# Get a Crasc Region by slug
@crasc_router.get("/region-crasc/{crasc_slug}", response_model=CrascRegionRead, status_code=status.HTTP_200_OK)
async def get_crasc_region_by_slug(crasc_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CrascRegion).where(CrascRegion.slug == crasc_slug)
    )
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Region CRASC non trouvé.")
    return region

# Get OSCs for a Crasc Region by slug
@crasc_router.get("/region-crasc/{crasc_slug}/oscs", response_model=CrascRegionReadWithOscs, status_code=status.HTTP_200_OK)
async def get_crasc_region_with_oscs_by_slug(crasc_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CrascRegion).options(selectinload(CrascRegion.oscs)).where(CrascRegion.slug == crasc_slug)
    )
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Region CRASC non trouvé.")
    return region

# Get OSCs and RegionCivs for a Crasc Region by slug
@crasc_router.get("/region-crasc/{crasc_slug}/details", response_model=CrascRegionReadWithOscsAndRegionCivs, status_code=status.HTTP_200_OK)
async def get_crasc_region_with_oscs_and_regioncivs_by_slug(crasc_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CrascRegion)
        .options(selectinload(CrascRegion.oscs))
        .options(selectinload(CrascRegion.regions_civ))
        .where(CrascRegion.slug == crasc_slug)
    )
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Region CRASC non trouvée.")
    return region

# CrascRegion update
@crasc_router.patch("/region-crasc/{crasc_slug}", response_model=CrascRegionRead, status_code=status.HTTP_200_OK)
async def update_crasc_region_by_slug(crasc_slug: str, crasc_region_update: CrascRegionUpdate, db: AsyncSession = Depends(get_db)) -> CrascRegion:
   # fetch existing resource by slug
   result = await db.execute(select(CrascRegion).where(CrascRegion.slug == crasc_slug))
   db_crasc_region = result.scalars().first()
   if not db_crasc_region:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Région CRASC non trouvée.")
   # extract fields provided in the request (exclude unset ones)
   update_data = crasc_region_update.model_dump(exclude_unset=True)
   # update the database object attributes
   for key, value in update_data.items():
      setattr(db_crasc_region, key, value)
   # persist changes
   await db.commit()
   await db.refresh(db_crasc_region)
   return db_crasc_region

######################
# OscType Endpoints. GET all/single, POST -> OK. Remaining PATCH, DELETE
######################
@crasc_router.post("/osc-type", response_model=OscTypeBase, status_code=status.HTTP_201_CREATED)
async def create_osc_type(osc_type: OscTypeCreate, db: AsyncSession = Depends(get_db)) -> OscType:
    # Check for duplicate name
    result = await db.execute(select(OscType).where(OscType.name == osc_type.name))
    existing_osc_type = result.scalars().first()
    if existing_osc_type:
        raise HTTPException(status_code=400, detail="Ce type de OSC existe déjà.")
    
    db_osc_type = OscType(**osc_type.model_dump())
    db.add(db_osc_type)
    await db.commit()
    await db.refresh(db_osc_type)
    return db_osc_type

@crasc_router.get("/osc-type", response_model=List[OscTypeReadWithOscs], status_code=status.HTTP_200_OK)
async def get_osc_types(db: AsyncSession = Depends(get_db)):
    statement = select(OscType).options(selectinload(OscType.oscs))
    result = await db.execute(statement.order_by(desc(OscType.name)))
    osc_types = result.scalars().all()
    return osc_types

@crasc_router.get("/osc-type/{osc_type_id}", response_model=OscTypeReadWithOscs, status_code=status.HTTP_200_OK)
async def get_osc_type(osc_type_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OscType).options(selectinload(OscType.oscs)).where(OscType.id == osc_type_id)
    )
    osc_type = result.scalars().first()
    if not osc_type:
        raise HTTPException(status_code=404, detail="Type de OSC non trouvé.")
    return osc_type

#@crasc_router.patch
#@crasc_router.delete

###############
# Osc Enpoints
###############
#@crasc_router.post("/osc", response_model=OscRead, status_code=status.HTTP_201_CREATED)
#async def create_osc(osc: OscCreate, db: AsyncSession = Depends(get_db)) -> OscRead:
#    # Validate that the type_id exists
#    result = await db.execute(select(OscType).where(OscType.id == osc.type_id))
#    osc_type = result.scalar_one_or_none()
#    if not osc_type:  
#      raise HTTPException(status_code=400, detail="Le type de OSC spécifié n'existe pas.")
#    
#    db_osc = Osc(**osc.model_dump())
#    db.add(db_osc)
#    await db.commit()
#    await db.refresh(db_osc)
#    return db_osc

@crasc_router.post("/osc", response_model=OscRead, status_code=status.HTTP_201_CREATED)
async def create_osc(osc: OscCreate, db: AsyncSession = Depends(get_db)) -> Osc:
    # Check for duplicate name
    osc_name_result = await db.execute(select(Osc).where(Osc.name == osc.name))
    existing_osc = osc_name_result.scalars().first()
    if existing_osc:
      raise HTTPException(status_code=400, detail="Cette OSC existe déjà.")
    # Validate that the type_id exists
    osc_type_result = await db.execute(select(OscType).where(OscType.id == osc.type_id))
    osc_type = osc_type_result.scalar_one_or_none()
    if not osc_type:  
      raise HTTPException(status_code=400, detail="Le type de OSC spécifié n'existe pas.")
    # Validate that the region_id exists
    crasc_region_result = await db.execute(select(CrascRegion).where(CrascRegion.id == osc.region_id))
    crasc_region = crasc_region_result.scalar_one_or_none()
    if not crasc_region:
      raise HTTPException(status_code=400, detail="Le CRASC spécifiée n'existe pas.")

    db_osc = Osc(**osc.model_dump())
    db.add(db_osc)
    await db.commit()
    await db.refresh(db_osc)
    return db_osc

@crasc_router.get("/osc-with-region-and-type", response_model=List[OscReadWithCrascRegionAndOscType], status_code=status.HTTP_200_OK)
async def get_oscs_with_region_and_type(
  db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100,
  type_id: Optional[int] = None, region_id: Optional[int] = None
):
  """ Get all OSCs with their CRASC region and Type info. Optional filtering by type_id and region_id. """
  statement = select(Osc).options(selectinload(Osc.type_osc)).options(selectinload(Osc.region_crasc)).offset(skip).limit(limit)
  if type_id:
    statement = statement.where(Osc.type_id == type_id)
  if region_id:
    statement = statement.where(Osc.region_id == region_id)
  result = await db.execute(statement.order_by(desc(Osc.name)))
  oscs = result.scalars().all()
  return [
    OscReadWithCrascRegionAndOscType(
      **osc.model_dump(),
      type=OscTypeRead.model_validate(osc.type_osc.model_dump()),
      region=CrascRegionRead.model_validate(osc.region_crasc.model_dump())
    )
    for osc in oscs
  ]

@crasc_router.get("/osc-with-region-and-type/{osc_id}", response_model=OscReadWithCrascRegionAndOscType, status_code=status.HTTP_200_OK)
async def get_osc_with_region_and_type(osc_id: int, db: AsyncSession = Depends(get_db)):
  """ Get a single OSC with its CRASC region and Type info. """
  result = await db.execute(
    select(Osc).options(
      selectinload(Osc.type_osc),
      selectinload(Osc.region_crasc)
    ).where(Osc.id == osc_id)
  )
  osc = result.scalars().first()
  if not osc:
    raise HTTPException(status_code=404, detail="OSC non trouvé.")
  return OscReadWithCrascRegionAndOscType(
    **osc.model_dump(),
    type=OscTypeRead.model_validate(osc.type_osc.model_dump()),
    region=CrascRegionRead.model_validate(osc.region_crasc.model_dump())
  )

###############
# NewsArticle Enpoints
###############
# Create News article (check for duplicate news title) and assign to OSC
@crasc_router.post("/osc-news", response_model=NewsArticleRead, status_code=status.HTTP_201_CREATED)
async def create_news_article_with_osc(article: NewsArticleCreate, db: AsyncSession = Depends(get_db)) -> NewsArticles:
  # Check for duplicate name
  result = await db.execute(select(NewsArticles).where(NewsArticles.title == article.title))
  existing_news_article = result.scalars().first()
  if existing_news_article:
    raise HTTPException(status_code=404, detail="Cette actualité existe déjà.")
  # Validate that the osc_id exists
  result = await db.execute(select(Osc).where(Osc.id == article.osc_id))
  osc = result.scalar_one_or_none()
  if not osc:
    raise HTTPException(status_code=400, detail="L'OSC' spécifiée n'existe pas.")
  db_article = NewsArticles(**article.model_dump())
  db.add(db_article)
  await db.commit()
  await db.refresh(db_article)
  return db_article

###############
# News Enpoints
###############
#@crasc_router.post("/news", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
#async def create_news(news: NewsCreate, db: AsyncSession = Depends(get_db)) -> News:
#  # Check for duplicate news title
#  result = await db.execute(select(News).where(News.title == news.title))
#  existing_news = result.scalars().first()
#  if existing_news:
#    raise HTTPException(status_code=404, detail="Cette actualité existe déjà.")
#  
#  db_news = News(**news.model_dump())
#  db.add(db_news)
#  await db.commit()
#  await db.refresh(db_news)
#  return db_news

@crasc_router.post("/news", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
async def create_news(
   title: str = Form(...),
   thumbnail: Optional[UploadFile] = File(None),
   crasc_id: str = Form(""),
   osc_id: str = Form(""),
   db: AsyncSession = Depends(get_db)
):
  # convert empty strings to None
  crasc_id_int = int(crasc_id) if crasc_id and crasc_id != "" else None
  osc_id_int = int(osc_id) if osc_id and osc_id != "" else None
  if thumbnail and thumbnail.filename:
    # User uploaded image: generate unique name and save
    file_extension = thumbnail.filename.split(".")[-1]
    # check for the extension to ensure users only upload images
    allowed_extensions = ["jpg", "jpeg", "png", "webp"]
    if file_extension.lower() not in allowed_extensions:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Format d'image invalide. Les formts valides sont: {allowed_extensions}.")
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
      shutil.copyfileobj(thumbnail.file, buffer)

    saved_path = filename
  else:
    # No file uploaded, use the default filename defined in your model
    saved_path = "default.png"
  
  # Create the database record
  news_create = News(
    title=title,
    crasc_id=crasc_id_int,
    osc_id=osc_id_int,
    thumbnail_path=saved_path
  )
    
  # Check for duplicate news title
  result = await db.execute(select(News).where(News.title == news_create.title))
  existing_news = result.scalars().first()
  if existing_news:
    raise HTTPException(status_code=404, detail="Cette actualité existe déjà.")
  
  db_news = News(**news_create.model_dump())
  db.add(db_news)
  await db.commit()
  await db.refresh(db_news)
  return db_news

@crasc_router.get("/news-with-crasc-and-osc", response_model=List[NewsReadWithCrascAndOsc], status_code=status.HTTP_200_OK)
async def get_news_with_crasc_and_osc(
  db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100,
  crasc_id: Optional[int] = None, osc_id: Optional[int] = None
):
  """ Get all News with their optional crasc region and osc. Optional filtering by crasc_id and osc_id. """
  statement = select(News).options(selectinload(News.crasc), selectinload(News.osc)).offset(skip).limit(limit).order_by(desc(News.id))

  if crasc_id:
    statement = statement.where(News.crasc_id == crasc_id)
  if osc_id:
    statement = statement.where(News.osc_id == osc_id)
  result = await db.execute(statement)
  all_news = result.scalars().all()
  return all_news

# News where crasc data is not null endpoint
@crasc_router.get("/news-crasc-related", response_model=List[NewsReadWithCrascAndOsc], status_code=status.HTTP_200_OK)
async def get_crasc_related_news(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get news articles that are related to CRASC (crasc_id is not null)
    """
    query = (
        select(News)
        .where(News.crasc_id.is_not(None))  # Filter news with crasc_id
        .options(
            joinedload(News.crasc),  # Eager load crasc relationship
            joinedload(News.osc)     # Eager load osc relationship
        )
        .offset(skip)
        .limit(limit)
        .order_by(News.id.desc())  # Most recent first
    )
    
    result = await db.execute(query)
    news_items = result.unique().scalars().all()
    return news_items

# Spotlight news per crasc: single (lastest) news per crasc
@crasc_router.get("/news-spotlight-per-crasc", response_model=List[NewsReadWithCrascAndOsc], status_code=status.HTTP_200_OK)
async def get_spotlight_news_per_crasc(
  db: AsyncSession = Depends(get_db)
):
  """
  Get spotlight news - one news per CRASC (optimized single query)
  """
  # Using DISTINCT ON for PostgreSQL (most efficient)
  query = (
    select(News)
    .distinct(News.crasc_id)  # PostgreSQL specific
    .where(News.crasc_id.is_not(None))
    .options(joinedload(News.crasc), joinedload(News.osc))
    .order_by(News.crasc_id, News.id.desc())  # Important: crasc_id first for DISTINCT ON
  )
  
  result = await db.execute(query)
  news_items = result.unique().scalars().all()

  return news_items