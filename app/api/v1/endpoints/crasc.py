import os, shutil, uuid, slugify
from fastapi import APIRouter, HTTPException, status, UploadFile, Depends, File, Form, Request, Query
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Annotated

from app.core.config import settings
from app.database.session import get_db
from app.schemas.crasc import (
   CrascRead,
   CrascReadDetail,
   CrascUpdate,
   RegionRead,
   RegionReadDetail,
   RegionUpdate,
   OscTypeRead,
   OscTypeReadDetail,
   OscTypeUpdate,
   OscRead,
   OscReadDetail,
   OscUpdate,
   NewsCreate,
   NewsRead,
   NewsReadDetail,
   NewsUpdate
)
from app.models.crasc import (
   Crasc, Region, OscType, Osc, News
)


crasc_router = APIRouter()


# Crasc Endpoints
@crasc_router.post("/crasc", response_model=CrascRead, status_code=status.HTTP_201_CREATED)
async def create_crasc(
   name: str = Form(...),
   description: Optional[str] = Form(None),
   osc_count: str = Form(""),
   db: AsyncSession = Depends(get_db)
):
   # convert empty strings to None
   osc_count_int = int(osc_count) if osc_count and osc_count != "" else None
   # create the database record
   crasc_create = Crasc(
      name=name,
      description=description,
      osc_count=osc_count_int
   )
   # check for duplicate crasc name
   result = await db.execute(
      select(Crasc).where(Crasc.name == crasc_create.name)
   )
   existing_crasc = result.scalars().first()
   if existing_crasc:
      raise HTTPException(
         status_code=status.HTTP_409_CONFLICT,
         detail={
            "type": "duplicate_error",
            "errors": [
              {
                "field": "name",
                "message": f"{existing_crasc.name} existe déjà. Veuillez choisir un nom différent."
              }
            ]
         }
      )
   try:
      db_crasc = Crasc(**crasc_create.model_dump())
      db.add(db_crasc)
      await db.commit()
      await db.refresh(db_crasc)
      return db_crasc
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


@crasc_router.get("/crasc", response_model=List[CrascReadDetail], status_code=status.HTTP_200_OK)
async def get_crascs(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """Get all CRASC with pagination"""
    result = await db.execute(
       select(Crasc)
       .options(selectinload(Crasc.regions))
       .options(selectinload(Crasc.oscs))
       .options(selectinload(Crasc.news_items))
       .offset(skip)
       .limit(limit)
       .order_by(Crasc.name)
    )
    crasc = result.scalars().all()
    return crasc


@crasc_router.get("/crasc/{crasc_slug}", response_model=CrascReadDetail, status_code=status.HTTP_200_OK)
async def get_crasc(crasc_slug: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(
      select(Crasc)
      .options(selectinload(Crasc.oscs))
      .options(selectinload(Crasc.regions))
      .options(selectinload(Crasc.news_items))
      .where(Crasc.slug == crasc_slug)
  )
  region = result.scalars().first()
  if not region:
    raise HTTPException(status_code=404, detail="CRASC non trouvé.")
  return region


@crasc_router.patch("/crasc/{crasc_slug}", response_model=CrascReadDetail, status_code=status.HTTP_200_OK)
async def update_crasc(crasc_slug: str, crasc_update: CrascUpdate, db: AsyncSession = Depends(get_db)): 
  # fetch existing resource by slug
  result = await db.execute(
    select(Crasc).where(Crasc.slug == crasc_slug)
    .options(selectinload(Crasc.oscs))
    .options(selectinload(Crasc.regions))
    .options(selectinload(Crasc.news_items))
  )
  crasc = result.scalars().first()
  if not crasc:
     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CRASC non trouvé.")
  # extract fields provided in the request (exclude unset ones)
  update_data = crasc_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(crasc, key, value)
  # update slug if name changed
  if "name" in update_data:
    crasc.slug = slugify.slugify(crasc.name)
  # persist changes
  await db.commit()
  await db.refresh(crasc)
  return crasc


@crasc_router.delete("/crasc/{crasc_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crasc(crasc_slug: str, db: AsyncSession = Depends(get_db)):
  # find crasc by slug
  result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
  crasc = result.scalar_one_or_none()
  # raise 404 if crasc does not exist
  if not crasc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"{crasc_slug} non trouvé."
    )
  await db.delete(crasc)
  await db.commit()
  return None


# Region Endpoints
@crasc_router.post("/region", response_model=RegionRead, status_code=status.HTTP_201_CREATED)
async def create_region(
  name: str = Form(...),
  crasc_id: str = Form(""),
  db: AsyncSession = Depends(get_db)
):
  # convert empty strings to None
  crasc_id_int = int(crasc_id) if crasc_id and crasc_id != "" else None
  # create the db record
  region_create = Region(
     name=name,
     crasc_id=crasc_id_int
  )
  # check for duplicate region name
  result = await db.execute(select(Region).where(Region.name == region_create.name))
  existing_region = result.scalars().first()
  if existing_region:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [
          {
            "field": "name",
            "message": f"La région {existing_region} existe déjà. Veuillez choisir un nom différent."
          }
        ]
      }
    )
  try:
    db_region = Region(**region_create.model_dump())
    db.add(db_region)
    await db.commit()
    await db.refresh(db_region)
    return db_region
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


@crasc_router.get("/region", response_model=list[RegionReadDetail], status_code=status.HTTP_200_OK)
async def get_regions(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """Get all regions with pagination"""
    result = await db.execute(
        select(Region)
        .options(joinedload(Region.crasc))
        .offset(skip)
        .limit(limit)
        .order_by(Region.name)
    )
    region = result.scalars().all()
    return region


@crasc_router.get("/region/{region_slug}", response_model=RegionReadDetail, status_code=status.HTTP_200_OK)
async def get_region(region_slug: str, db: AsyncSession = Depends(get_db)):
  result = await db.execute(
    select(Region).where(Region.slug == region_slug).options(selectinload(Region.crasc))
  )
  region = result.scalars().first()
  if not region:
    raise HTTPException(status_code=404, detail="Région non trouvée.")
  return region


@crasc_router.patch("/region/{region_slug}", response_model=RegionReadDetail, status_code=status.HTTP_200_OK)
async def update_region_civ_by_slug(region_slug: str, region_update: RegionUpdate, db: AsyncSession = Depends(get_db)):
  # fetch existing resource by slug
  result = await db.execute(
    select(Region).where(Region.slug == region_slug).options(selectinload(Region.crasc))
  )
  region = result.scalars().first()
  if not region:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Région non trouvée.")
  # extract fields provided in the request (exclude unset ones)
  update_data = region_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(region, key, value)
  # update slug if name changed
  if "name" in update_data:
     region.slug = slugify.slugify(region.name)

  # persist changes
  await db.commit()
  await db.refresh(region)
  return region


@crasc_router.delete("/region/{region_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_region(region_slug: str, db: AsyncSession = Depends(get_db)):
  # find region by slug
  result = await db.execute(select(Region).where(Region.slug == region_slug))
  region = result.scalar_one_or_none()
  # raise 404 if team does not exist
  if not region:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Region: {region_slug} non trouvé."
    )
  await db.delete(region)
  await db.commit()
  return None


# OscType Endpoints.
@crasc_router.post("/osc-type", response_model=OscTypeRead, status_code=status.HTTP_201_CREATED)
async def create_osc_type(
   name: str = Form(...),
   description: Optional[str] = Form(None),
   db: AsyncSession = Depends(get_db)
) -> OscType:
    # create the db record
    osctype_create = OscType(
       name=name,
       description=description
    )
    # Check for duplicate name
    result = await db.execute(select(OscType).where(OscType.name == osctype_create.name))
    existing_osc_type = result.scalars().first()
    if existing_osc_type:
        raise HTTPException(
           status_code=status.HTTP_409_CONFLICT,
           detail={
              "type": "duplicate_error",
              "errors": [
                 {
                    "field": "name",
                    "message": f"Le type {existing_osc_type.name} existe déjà." 
                 }
              ]
            }
        )
    try:
       db_osctype = OscType(**osctype_create.model_dump())
       db.add(db_osctype)
       await db.commit()
       await db.refresh(db_osctype)
       return db_osctype
    except Exception as e:
      await db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
          "type": "database_error",
          "errors": [
            {
              "field": "database",
              "message": f"Erreur lors de la création du type de osc: {str(e)}"
            }
          ]
        }
      )

@crasc_router.get("/osc-type", response_model=List[OscTypeReadDetail], status_code=status.HTTP_200_OK)
async def get_all_osc_type(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'enregistrements à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """Get all OSC types with pagination"""
    query = await db.execute(
       select(OscType)
       .options(selectinload(OscType.oscs))
       .offset(skip)
       .limit(limit)
       .order_by(OscType.name)
    )
    osc_types = query.scalars().all()
    return osc_types

@crasc_router.get("/osc-type/{osctype_slug}", response_model=OscTypeReadDetail, status_code=status.HTTP_200_OK)
async def get_single_osc_type(osctype_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OscType).options(selectinload(OscType.oscs)).where(OscType.slug == osctype_slug)
    )
    osc_type = result.scalars().first()
    if not osc_type:
        raise HTTPException(status_code=404, detail="Type de OSC non trouvé.")
    return osc_type


@crasc_router.patch("/osc-type/{osctype_slug}", response_model=OscTypeRead, status_code=status.HTTP_200_OK)
async def update_osc_type(osctype_slug: str, osctype_update: OscTypeUpdate, db: AsyncSession = Depends(get_db)):
  # fetch existing resource by slug
  result = await db.execute(
    select(OscType).where(OscType.slug == osctype_slug).options(selectinload(OscType.oscs))
  )
  osctype = result.scalars().first()
  if not osctype:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Type de OSC non trouvé.")
  # extract fields provided in the request (exclude unset ones)
  update_data = osctype_update.model_dump(exclude_unset=True)
  # update the database object attributes
  for key, value in update_data.items():
    setattr(osctype, key, value)
  # update slug if name changed
  if "name" in update_data:
     osctype.slug = slugify.slugify(osctype.name)
  
  # persist changes
  await db.commit()
  await db.refresh(osctype)
  return osctype


@crasc_router.delete("/osc-type/{osctype_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_osc_type(osctype_slug: str, db: AsyncSession = Depends(get_db)):
  # find osc type by slug
  result = await db.execute(select(OscType).where(OscType.slug == osctype_slug))
  osctype = result.scalar_one_or_none()
  # raise 404 if osctype does not exist
  if not osctype:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Type de OSC {osctype_slug} non trouvé."
    )
  await db.delete(osctype)
  await db.commit()
  return None


# Osc Enpoints
@crasc_router.post("/osc", response_model=OscRead, status_code=status.HTTP_201_CREATED)
async def create_osc(
  name: str = Form(...),
  description: Optional[str] = Form(None),
  thumbnail: Optional[UploadFile] = File(None),
  type_id: str = Form(""),
  crasc_id: str = Form(""),
  db: AsyncSession = Depends(get_db)
):
  # convert empty strings to None
  type_id_int = int(type_id) if type_id and type_id != "" else None
  crasc_id_int = int(crasc_id) if crasc_id and crasc_id != "" else None
  
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
  
  # Create the database record
  db_osc = Osc(
    name=name,
    description=description,
    thumbnail_path=saved_path,
    type_id=type_id_int,
    crasc_id=crasc_id_int,
  )
    
  # Check for duplicate osc name
  result = await db.execute(select(Osc).where(Osc.name == db_osc.name))
  existing_news = result.scalars().first()
  if existing_news:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [
          {
            "field": "name",
            "message": "Une OSC avec ce nom existe déjà. Veuillez choisir un nom différent."
          }
        ]
      }
    )
  try:
    osc_create = Osc(**db_osc.model_dump())
    db.add(osc_create)
    await db.commit()
    await db.refresh(osc_create)
    return osc_create
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


@crasc_router.get("/osc", response_model=List[OscReadDetail], status_code=status.HTTP_200_OK)
async def get_all_osc(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    type_id: Optional[int] = Query(None, description="Filter by OSC type ID"),
    crasc_id: Optional[int] = Query(None, description="Filter by CRASC ID"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all OSC with optional filtering and pagination
    """
    query = select(Osc).options(
        selectinload(Osc.type),
        selectinload(Osc.crasc),
        selectinload(Osc.news_items)
    )
    
    # Apply filters
    if type_id:
        query = query.where(Osc.type_id == type_id)
    
    if crasc_id:
        query = query.where(Osc.crasc_id == crasc_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Osc.name.ilike(search_term)) | 
            (Osc.description.ilike(search_term))
        )
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Osc.name)
    
    result = await db.execute(query)
    osc_list = result.scalars().all()
    
    return osc_list


@crasc_router.get("/osc/{osc_slug}", response_model=OscReadDetail, status_code=status.HTTP_200_OK)
async def get_osc_by_slug(
    osc_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single OSC by slug with all relationships
    """
    query = select(Osc).where(Osc.slug == osc_slug).options(
        selectinload(Osc.type),
        selectinload(Osc.crasc),
        selectinload(Osc.news_items)
    )
    
    result = await db.execute(query)
    osc = result.scalar_one_or_none()
    
    if not osc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OSC non trouvée"
        )
    
    return osc


async def get_osc_update_form(
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    type_id: str = Form(""),
    crasc_id: str = Form(""),
    address: Optional[str] = Form("")
) -> OscUpdate:
    """Parse form data into OscUpdate"""
    # Parse numeric fields
    parsed_type_id = int(type_id) if type_id and type_id != "" else None
    parsed_crasc_id = int(crasc_id) if crasc_id and crasc_id != "" else None
    
    return OscUpdate(
        name=name,
        description=description,
        type_id=parsed_type_id,
        crasc_id=parsed_crasc_id,
        address=address
    )

@crasc_router.patch("/osc/{osc_slug}", response_model=OscRead)
async def update_osc_with_form(
    osc_slug: str,
    osc_update: OscUpdate = Depends(get_osc_update_form),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Update OSC with optional thumbnail upload
    """
    # Fetch the OSC
    result = await db.execute(
      select(Osc).where(Osc.slug == osc_slug).options(selectinload(Osc.type), selectinload(Osc.crasc))
    )
    osc = result.scalars().first()
    
    if not osc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OSC non trouvée")
    
    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
        # Validate file
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        file_extension = thumbnail.filename.split(".")[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format d'image invalide. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Save new thumbnail
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        
        osc.thumbnail_path = filename
    
    # Update other fields (same logic as regular PATCH)
    update_data = osc_update.model_dump(exclude_unset=True)
    # Update remaining fields
    for key, value in update_data.items():
       setattr(osc, key, value)
    if "name" in update_data:
      osc.slug = slugify.slugify(osc.name)
    
    try:
        #db.add(osc)
        await db.commit()
        await db.refresh(osc)
        return osc
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
              "type": "database_error",
              "errors": [
                {
                  "field": "database",
                  "message": f"Erreur lors de la création de l'OSC: {str(e)}"
                }
              ]
            }
        )


@crasc_router.delete("/osc/{osc_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_osc(osc_slug: str, db: AsyncSession = Depends(get_db)):
   result = await db.execute(
      select(Osc).where(Osc.slug == osc_slug)
   )
   osc = result.scalar_one_or_none()
   if not osc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Osc {osc_slug} non trouvée."
    )
   
   await db.delete(osc)
   await db.commit()
   return None


@crasc_router.post("/news", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
async def create_news(
   title: str = Form(...),
   content: Optional[str] = Form(None),
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
  
  # Create the database record
  news_create = News(
    title=title,
    content=content,
    crasc_id=crasc_id_int,
    osc_id=osc_id_int,
    thumbnail_path=saved_path
  )
    
  # Check for duplicate news title
  result = await db.execute(select(News).where(News.title == news_create.title))
  existing_news = result.scalars().first()
  if existing_news:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "type": "duplicate_error",
        "errors": [
          {
            "field": "title",
            "message": "Une actualité avec ce titre existe déjà. Veuillez choisir un titre différent."
          }
        ]
      }
    )
  try:
    db_news = News(**news_create.model_dump())
    db.add(db_news)
    await db.commit()
    await db.refresh(db_news)
    return db_news
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


@crasc_router.get("/news", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
async def get_all_news(
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


@crasc_router.get("/news/{news_slug}", response_model=NewsReadDetail, status_code=status.HTTP_200_OK)
async def get_single_news_item(
   news_slug: str,
   db: AsyncSession = Depends(get_db)
):
   query = select(News).where(News.slug == news_slug).options(
      selectinload(News.crasc),
      selectinload(News.osc)
   )
   result = await db.execute(query)
   news = result.scalar_one_or_none()
   if not news:
      raise HTTPException(
         status_code=status.HTTP_404_NOT_FOUND,
         detail="Actualité non trouvée."
      )
   return news
#   result = await db.execute(
#      select(News).options(selectinload(News.crasc), selectinload(News.osc)).where(News.slug == news_slug)
#   )
#   news = result.scalars().all()
#   return news

# update

@crasc_router.delete("/news/{news_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(news_slug: str, db: AsyncSession = Depends(get_db)):
  # find news item by slug
  result = await db.execute(select(News).where(News.slug == news_slug))
  news = result.scalar_one_or_none()
  # raise 404 if team does not exist
  if not news:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Article {news_slug} non trouvé."
    )
  await db.delete(news)
  await db.commit()
  return None

## Special GET: Spotlight news per crasc: single (lastest) news per crasc
@crasc_router.get("/news-spotlight-crasc", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
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