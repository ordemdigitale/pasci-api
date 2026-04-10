from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict
from pydantic import BaseModel

from app.database.session import get_db
from app.models.site_config import SiteConfig

site_config_router = APIRouter()


class ConfigUpdate(BaseModel):
    value: str


@site_config_router.get("", response_model=Dict[str, str])
async def get_all_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SiteConfig))
    rows = result.scalars().all()
    return {r.key: r.value or "" for r in rows}


@site_config_router.put("/{key}")
async def upsert_config(key: str, body: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
    row = result.scalars().first()
    if row:
        row.value = body.value
    else:
        row = SiteConfig(key=key, value=body.value)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"key": row.key, "value": row.value}
