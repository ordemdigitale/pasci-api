from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List

from app.database.session import get_db
from app.schemas.crasc import (
  RegionCivCreate,
  RegionCivRead,
  OscTypeBase,
  OscTypeCreate,
  OscTypeRead,
  OscTypeReadWithOscs,
  OscCreate,
  OscRead,
  OscReadWithCrascRegionAndOscType,
  OscReadWithOscType,
  OscReadWithCrascRegion,
  CrascRegionBase,
  CrascRegionCreate,
  CrascRegionRead,
  CrascRegionReadWithOscs,
  CrascRegionReadWithOscsAndRegionCivs
)
from app.models.crasc import RegionCiv, CrascRegion, OscType, Osc

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

@crasc_router.get("/region-civ", response_model=list[RegionCiv], status_code=status.HTTP_200_OK)
async def get_region_civs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCiv).order_by(desc(RegionCiv.name)))
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
        raise HTTPException(status_code=404, detail="Region CRASC non trouvé.")
    return region

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
      raise HTTPException(status_code=400, detail="La région CRASC spécifiée n'existe pas.")

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