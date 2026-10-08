# app/api/v1/endpoints/ressource_typologie.py | Types et catégories de ressources (gérés dans l'admin)
from typing import List, Optional

import slugify
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_staff_user
from app.database.session import get_db
from app.models.documentation import Documentation
from app.models.ressource_typologie import RessourceCategorie, RessourceType
from app.models.users import User

ressource_typologie_router = APIRouter()


class TypeRead(BaseModel):
    id: int
    slug: str
    nom: str
    description: Optional[str] = None
    ordre: int
    actif: bool
    nb_documents: int = 0


class TypeEcriture(BaseModel):
    nom: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    ordre: Optional[int] = None
    actif: Optional[bool] = None


class CategorieRead(BaseModel):
    id: int
    nom: str
    type_slug: Optional[str] = None
    ordre: int
    actif: bool
    nb_documents: int = 0


class CategorieEcriture(BaseModel):
    nom: str = Field(min_length=2, max_length=100)
    type_slug: Optional[str] = None
    ordre: Optional[int] = None
    actif: Optional[bool] = None


async def _compter(db: AsyncSession, colonne) -> dict:
    rows = await db.execute(select(colonne, func.count()).group_by(colonne))
    return {valeur: n for valeur, n in rows.all()}


async def _type_existe(db: AsyncSession, slug: str) -> bool:
    return (await db.execute(select(RessourceType.id).where(RessourceType.slug == slug))).first() is not None


async def _categorie_en_double(db: AsyncSession, nom: str, type_slug: Optional[str], sauf_id: Optional[int] = None) -> bool:
    q = select(RessourceCategorie.id).where(
        func.lower(RessourceCategorie.nom) == nom.lower(),
        RessourceCategorie.type_slug.is_(None) if type_slug is None else RessourceCategorie.type_slug == type_slug,
    )
    if sauf_id:
        q = q.where(RessourceCategorie.id != sauf_id)
    return (await db.execute(q)).first() is not None


# ── Types ─────────────────────────────────────────────────────────────

@ressource_typologie_router.get("/types", response_model=List[TypeRead])
async def lister_types(
    tous: bool = Query(False, description="Inclure les types désactivés (admin)"),
    db: AsyncSession = Depends(get_db),
):
    q = select(RessourceType).order_by(RessourceType.ordre, RessourceType.nom)
    if not tous:
        q = q.where(RessourceType.actif == True)  # noqa: E712
    types = (await db.execute(q)).scalars().all()
    nb = await _compter(db, Documentation.type)
    return [TypeRead(**t.model_dump(), nb_documents=nb.get(t.slug, 0)) for t in types]


@ressource_typologie_router.post("/types", response_model=TypeRead, status_code=status.HTTP_201_CREATED)
async def creer_type(
    payload: TypeEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    slug = slugify.slugify(payload.nom.strip())[:50]
    if not slug:
        raise HTTPException(status_code=422, detail="Nom de type invalide.")
    if await _type_existe(db, slug):
        raise HTTPException(status_code=409, detail="Ce type existe déjà.")
    if payload.ordre is None:
        dernier = (await db.execute(select(func.max(RessourceType.ordre)))).scalar() or 0
        payload.ordre = dernier + 1
    t = RessourceType(slug=slug, nom=payload.nom.strip(), description=payload.description,
                      ordre=payload.ordre, actif=True if payload.actif is None else payload.actif)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return TypeRead(**t.model_dump())


@ressource_typologie_router.patch("/types/{type_id}", response_model=TypeRead)
async def modifier_type(
    type_id: int,
    payload: TypeEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Le slug (valeur stockée dans les documents) ne change pas : seul le libellé est modifié."""
    t = await db.get(RessourceType, type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Type introuvable.")
    t.nom = payload.nom.strip()
    t.description = payload.description
    if payload.ordre is not None:
        t.ordre = payload.ordre
    if payload.actif is not None:
        t.actif = payload.actif
    await db.commit()
    await db.refresh(t)
    nb = await _compter(db, Documentation.type)
    return TypeRead(**t.model_dump(), nb_documents=nb.get(t.slug, 0))


@ressource_typologie_router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_type(
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    t = await db.get(RessourceType, type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Type introuvable.")
    utilises = (await db.execute(select(func.count()).select_from(Documentation).where(Documentation.type == t.slug))).scalar()
    if utilises:
        raise HTTPException(
            status_code=409,
            detail=f"{utilises} ressource(s) utilisent ce type : désactivez-le plutôt que de le supprimer.",
        )
    # Les catégories propres à ce type deviennent communes à tous les types
    await db.execute(update(RessourceCategorie).where(RessourceCategorie.type_slug == t.slug).values(type_slug=None))
    await db.delete(t)
    await db.commit()


# ── Catégories ────────────────────────────────────────────────────────

@ressource_typologie_router.get("/categories", response_model=List[CategorieRead])
async def lister_categories(
    type: Optional[str] = Query(None, description="Catégories proposées pour ce type (et communes)"),
    tous: bool = Query(False, description="Inclure les catégories désactivées (admin)"),
    db: AsyncSession = Depends(get_db),
):
    q = select(RessourceCategorie).order_by(RessourceCategorie.type_slug.nulls_first(), RessourceCategorie.ordre, RessourceCategorie.nom)
    if not tous:
        q = q.where(RessourceCategorie.actif == True)  # noqa: E712
    if type:
        q = q.where((RessourceCategorie.type_slug == type) | RessourceCategorie.type_slug.is_(None))
    cats = (await db.execute(q)).scalars().all()
    nb = await _compter(db, Documentation.category)
    return [CategorieRead(**c.model_dump(), nb_documents=nb.get(c.nom, 0)) for c in cats]


@ressource_typologie_router.post("/categories", response_model=CategorieRead, status_code=status.HTTP_201_CREATED)
async def creer_categorie(
    payload: CategorieEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    nom = payload.nom.strip()
    if payload.type_slug and not await _type_existe(db, payload.type_slug):
        raise HTTPException(status_code=422, detail="Type de ressource inconnu.")
    if await _categorie_en_double(db, nom, payload.type_slug):
        raise HTTPException(status_code=409, detail="Cette catégorie existe déjà pour ce type.")
    if payload.ordre is None:
        dernier = (await db.execute(select(func.max(RessourceCategorie.ordre)))).scalar() or 0
        payload.ordre = dernier + 1
    c = RessourceCategorie(nom=nom, type_slug=payload.type_slug or None, ordre=payload.ordre,
                           actif=True if payload.actif is None else payload.actif)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CategorieRead(**c.model_dump())


@ressource_typologie_router.patch("/categories/{categorie_id}", response_model=CategorieRead)
async def modifier_categorie(
    categorie_id: int,
    payload: CategorieEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Renommer une catégorie met à jour les ressources qui la portent."""
    c = await db.get(RessourceCategorie, categorie_id)
    if not c:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")
    nom = payload.nom.strip()
    if payload.type_slug and not await _type_existe(db, payload.type_slug):
        raise HTTPException(status_code=422, detail="Type de ressource inconnu.")
    if await _categorie_en_double(db, nom, payload.type_slug or None, sauf_id=c.id):
        raise HTTPException(status_code=409, detail="Cette catégorie existe déjà pour ce type.")
    if nom != c.nom:
        q = update(Documentation).where(Documentation.category == c.nom)
        if c.type_slug:
            q = q.where(Documentation.type == c.type_slug)
        await db.execute(q.values(category=nom))
    c.nom = nom
    c.type_slug = payload.type_slug or None
    if payload.ordre is not None:
        c.ordre = payload.ordre
    if payload.actif is not None:
        c.actif = payload.actif
    await db.commit()
    await db.refresh(c)
    nb = await _compter(db, Documentation.category)
    return CategorieRead(**c.model_dump(), nb_documents=nb.get(c.nom, 0))


@ressource_typologie_router.delete("/categories/{categorie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_categorie(
    categorie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    c = await db.get(RessourceCategorie, categorie_id)
    if not c:
        raise HTTPException(status_code=404, detail="Catégorie introuvable.")
    utilises = (await db.execute(
        select(func.count()).select_from(Documentation).where(Documentation.category == c.nom)
    )).scalar()
    if utilises:
        raise HTTPException(
            status_code=409,
            detail=f"{utilises} ressource(s) utilisent cette catégorie : désactivez-la plutôt que de la supprimer.",
        )
    await db.delete(c)
    await db.commit()
