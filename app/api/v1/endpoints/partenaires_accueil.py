# endpoints/partenaires_accueil.py | Section « Nos partenaires » de l'accueil (logos gérés dans l'admin)
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, computed_field
from sqlmodel import asc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.endpoints.hero_slides import _delete_image, _save_image
from app.core.auth import get_current_staff_user, get_optional_current_user
from app.core.config import settings
from app.database.session import get_db
from app.models.partenaire_accueil import PartenaireAccueil
from app.models.users import User

partenaires_accueil_router = APIRouter()


class PartenaireRead(BaseModel):
    id: int
    nom: str
    logo_path: Optional[str] = None
    site_web: Optional[str] = None
    ordre: int
    actif: bool

    @computed_field
    @property
    def logo_url(self) -> Optional[str]:
        """Chemin du site web (« /images/… ») tel quel, sinon fichier servi par l'API."""
        if not self.logo_path:
            return None
        if self.logo_path.startswith("/") or self.logo_path.startswith("http"):
            return self.logo_path
        return f"{settings.API_BASE_URL}/static/{self.logo_path}"

    class Config:
        from_attributes = True


def _site_web(valeur: Optional[str]) -> Optional[str]:
    v = (valeur or "").strip()
    if not v:
        return None
    if not v.startswith(("http://", "https://")):
        v = f"https://{v}"
    return v[:500]


@partenaires_accueil_router.get("", response_model=List[PartenaireRead])
async def lister_partenaires(
    tous: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    q = select(PartenaireAccueil).order_by(asc(PartenaireAccueil.ordre), asc(PartenaireAccueil.id))
    est_staff = bool(current_user and (current_user.is_staff or current_user.is_superuser))
    if not (tous and est_staff):
        q = q.where(PartenaireAccueil.actif == True)  # noqa: E712
    return (await db.execute(q)).scalars().all()


@partenaires_accueil_router.post("", response_model=PartenaireRead, status_code=status.HTTP_201_CREATED)
async def creer_partenaire(
    nom: str = Form(...),
    site_web: Optional[str] = Form(default=None),
    ordre: Optional[int] = Form(default=None),
    actif: bool = Form(default=True),
    logo: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    if not nom.strip():
        raise HTTPException(status_code=422, detail="Le nom est requis.")
    if ordre is None:
        existants = (await db.execute(select(PartenaireAccueil.ordre))).scalars().all()
        ordre = (max(existants) + 1) if existants else 0
    p = PartenaireAccueil(
        nom=nom.strip()[:200], site_web=_site_web(site_web), ordre=ordre, actif=actif,
        logo_path=_save_image(logo) if logo and logo.filename else None,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@partenaires_accueil_router.patch("/{partenaire_id}", response_model=PartenaireRead)
async def modifier_partenaire(
    partenaire_id: int,
    nom: Optional[str] = Form(default=None),
    site_web: Optional[str] = Form(default=None),
    ordre: Optional[int] = Form(default=None),
    actif: Optional[bool] = Form(default=None),
    logo: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    p = await db.get(PartenaireAccueil, partenaire_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partenaire introuvable.")
    if nom is not None:
        if not nom.strip():
            raise HTTPException(status_code=422, detail="Le nom est requis.")
        p.nom = nom.strip()[:200]
    if site_web is not None:
        p.site_web = _site_web(site_web)
    if ordre is not None:
        p.ordre = ordre
    if actif is not None:
        p.actif = actif
    if logo and logo.filename:
        _delete_image(p.logo_path)
        p.logo_path = _save_image(logo)
    await db.commit()
    await db.refresh(p)
    return p


@partenaires_accueil_router.delete("/{partenaire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_partenaire(
    partenaire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    p = await db.get(PartenaireAccueil, partenaire_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partenaire introuvable.")
    _delete_image(p.logo_path)
    await db.delete(p)
    await db.commit()
