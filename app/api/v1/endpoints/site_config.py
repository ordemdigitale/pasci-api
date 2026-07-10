import os, shutil, uuid
from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict
from pydantic import BaseModel

from app.database.session import get_db
from app.models.site_config import SiteConfig
from app.core.config import settings

site_config_router = APIRouter()


class ConfigUpdate(BaseModel):
    value: str


class PaymentNumbersRead(BaseModel):
    wave_number: str
    orange_money_number: str


async def get_config_value(db: AsyncSession, key: str, fallback: str) -> str:
    result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
    row = result.scalars().first()
    return row.value if row and row.value else fallback


@site_config_router.get("", response_model=Dict[str, str])
async def get_all_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SiteConfig))
    rows = result.scalars().all()
    return {r.key: r.value or "" for r in rows}


@site_config_router.get("/payment-numbers", response_model=PaymentNumbersRead)
async def get_payment_numbers(db: AsyncSession = Depends(get_db)):
    return PaymentNumbersRead(
        wave_number=await get_config_value(db, "payment_wave_number", settings.WAVE_NUMBER),
        orange_money_number=await get_config_value(db, "payment_orange_money_number", settings.ORANGE_MONEY_NUMBER),
    )


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


@site_config_router.post("/upload/{key}")
async def upload_config_image(key: str, image: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload an image and store its URL in site config."""
    ext = image.filename.rsplit(".", 1)[-1].lower() if image.filename and "." in image.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(image.file, f)
    image_url = f"{settings.API_BASE_URL}/static/{filename}"

    result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
    row = result.scalars().first()
    if row:
        # delete old file if it's a stored upload
        if row.value and "/static/" in row.value:
            old_filename = row.value.split("/static/")[-1]
            old_path = os.path.join(settings.UPLOAD_DIR, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
        row.value = image_url
    else:
        row = SiteConfig(key=key, value=image_url)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"key": row.key, "value": row.value}
