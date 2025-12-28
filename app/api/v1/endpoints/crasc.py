from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.database.session import get_db
from app.schemas.crasc import (
    OscTypeCreate,
    OscTypeUpdate,
    OscTypeRead,
    OscCreate,
    OscRead,
)
from app.models.crasc import OscType, Osc

crasc_router = APIRouter()

# OscType Endpoints
@crasc_router.post("/osc-type", response_model=OscTypeRead, status_code=status.HTTP_201_CREATED)
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

@crasc_router.get("/osc-type", response_model=list[OscTypeRead], status_code=status.HTTP_200_OK)
async def get_osc_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OscType).order_by(desc(OscType.name)))
    osc_types = result.scalars().all()
    return osc_types

# Osc Enpoints
@crasc_router.post("/osc", response_model=OscRead, status_code=status.HTTP_201_CREATED)
async def create_osc(osc: OscCreate, db: AsyncSession = Depends(get_db)) -> Osc:
    # Validate that the type_id exists
    if not db.get(OscType, osc.type_id):
        raise HTTPException(status_code=400, detail="Le type de OSC spécifié n'existe pas.")
    
    db_osc = Osc(**osc.model_dump())
    db.add(db_osc)
    await db.commit()
    await db.refresh(db_osc)
    return db_osc

@crasc_router.get("/osc", response_model=list[OscRead], status_code=status.HTTP_200_OK)
async def get_oscs(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100, type_id: Optional[int] = None):
    statement = select(Osc).offset(skip).limit(limit)

    if type_id:
        statement = statement.where(Osc.type_id == type_id)
        
    result = await db.execute(statement.order_by(desc(Osc.name)))
    oscs = result.scalars().all()
    return oscs