import os, re, shutil, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict
from pydantic import BaseModel

from app.database.session import get_db
from app.models.site_config import SiteConfig
from app.core.config import settings
from app.core.auth import get_current_staff_user
from app.models.users import User

site_config_router = APIRouter()


# Images de configuration (illustrations des pages, image par défaut…)
EXTENSIONS_IMAGE = {"jpg", "jpeg", "png", "webp"}
TAILLE_MAX_IMAGE = 5 * 1024 * 1024
CLE_VALIDE = re.compile(r"^[a-z0-9_]{1,100}$")
# Médias de l'accueil (podcast, vidéo) : audio ou vidéo, 100 Mo maximum
EXTENSIONS_MEDIA = {"mp3", "m4a", "aac", "ogg", "oga", "wav", "mp4", "webm", "mov"}
TAILLE_MAX_MEDIA = 100 * 1024 * 1024


def _verifier_cle(key: str) -> None:
    if not CLE_VALIDE.match(key):
        raise HTTPException(status_code=422, detail="Clé de configuration invalide.")


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
async def upsert_config(
    key: str,
    body: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    # Réservé à l'administration : auparavant n'importe qui pouvait modifier la configuration.
    _verifier_cle(key)
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
async def upload_config_image(
    key: str,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Upload an image and store its URL in site config (administration uniquement)."""
    _verifier_cle(key)
    ext = image.filename.rsplit(".", 1)[-1].lower() if image.filename and "." in image.filename else ""
    if ext not in EXTENSIONS_IMAGE:
        raise HTTPException(status_code=422, detail="Format d'image non supporté (JPG, PNG ou WEBP).")
    image.file.seek(0, os.SEEK_END)
    taille = image.file.tell()
    image.file.seek(0)
    if taille > TAILLE_MAX_IMAGE:
        raise HTTPException(status_code=413, detail="Image trop lourde (5 Mo maximum).")
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
            old_filename = os.path.basename(row.value.split("/static/")[-1])
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


@site_config_router.post("/upload-media/{key}")
async def upload_config_media(
    key: str,
    fichier: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Envoi d'un fichier audio ou vidéo (podcast, vidéo de l'accueil) ; son URL est stockée sous `key`."""
    _verifier_cle(key)
    ext = fichier.filename.rsplit(".", 1)[-1].lower() if fichier.filename and "." in fichier.filename else ""
    if ext not in EXTENSIONS_MEDIA:
        raise HTTPException(status_code=422, detail="Format non supporté (MP3, M4A, AAC, OGG, WAV, MP4, WEBM, MOV).")
    fichier.file.seek(0, os.SEEK_END)
    taille = fichier.file.tell()
    fichier.file.seek(0)
    if taille > TAILLE_MAX_MEDIA:
        raise HTTPException(status_code=413, detail="Fichier trop lourd (100 Mo maximum).")
    dossier = os.path.join(settings.UPLOAD_DIR, "accueil-medias")
    os.makedirs(dossier, exist_ok=True)
    filename = f"{uuid.uuid4()}.{ext}"
    with open(os.path.join(dossier, filename), "wb") as f:
        shutil.copyfileobj(fichier.file, f)
    url = f"{settings.API_BASE_URL}/static/accueil-medias/{filename}"

    row = (await db.execute(select(SiteConfig).where(SiteConfig.key == key))).scalars().first()
    if row:
        if row.value and "/static/accueil-medias/" in row.value:
            ancien = os.path.join(dossier, os.path.basename(row.value))
            if os.path.exists(ancien):
                os.remove(ancien)
        row.value = url
    else:
        row = SiteConfig(key=key, value=url)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"key": row.key, "value": row.value}
