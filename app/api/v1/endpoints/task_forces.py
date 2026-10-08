# endpoints/task_forces.py | Task forces thématiques des PTF (annuaire PTF)
from typing import List, Optional

import slugify
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlmodel import asc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_staff_user, get_optional_current_user
from app.core.config import settings
from app.database.session import get_db
from app.models.ptf import Ptf
from app.models.task_force import TaskForce, TaskForcePtf
from app.models.users import User

task_forces_router = APIRouter()


class MembreRead(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    categorie: Optional[str] = None
    thumbnail_url: Optional[str] = None
    chef_de_file: bool = False


class TaskForceRead(BaseModel):
    id: int
    nom: str
    slug: str
    thematique: str
    description: Optional[str] = None
    ordre: int
    actif: bool
    membres: List[MembreRead] = []


class TaskForceEcriture(BaseModel):
    nom: str = Field(min_length=3, max_length=200)
    thematique: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    ordre: int = 0
    actif: bool = True
    ptf_ids: List[int] = []
    chef_de_file_id: Optional[int] = None


def _vignette(ptf: Ptf) -> Optional[str]:
    if ptf.thumbnail_path and ptf.thumbnail_path != "default.png":
        return f"{settings.API_BASE_URL}/static/{ptf.thumbnail_path}"
    return None


async def _lire(db: AsyncSession, tf: TaskForce) -> TaskForceRead:
    rows = (await db.execute(
        select(Ptf, TaskForcePtf.chef_de_file)
        .join(TaskForcePtf, TaskForcePtf.ptf_id == Ptf.id)
        .where(TaskForcePtf.task_force_id == tf.id)
        .order_by(TaskForcePtf.chef_de_file.desc(), Ptf.name)
    )).all()
    membres = [
        MembreRead(id=p.id, name=p.name, slug=p.slug, categorie=p.categorie, thumbnail_url=_vignette(p), chef_de_file=chef)
        for p, chef in rows
    ]
    return TaskForceRead(**tf.model_dump(), membres=membres)


async def _enregistrer_membres(db: AsyncSession, tf: TaskForce, payload: TaskForceEcriture) -> None:
    ids = list(dict.fromkeys(payload.ptf_ids))
    if ids:
        existants = set((await db.execute(select(Ptf.id).where(Ptf.id.in_(ids)))).scalars().all())
        inconnus = [i for i in ids if i not in existants]
        if inconnus:
            raise HTTPException(status_code=422, detail=f"PTF inconnu(s) : {inconnus}")
    if payload.chef_de_file_id and payload.chef_de_file_id not in ids:
        raise HTTPException(status_code=422, detail="Le chef de file doit être membre de la task force.")
    await db.execute(delete(TaskForcePtf).where(TaskForcePtf.task_force_id == tf.id))
    for i in ids:
        db.add(TaskForcePtf(task_force_id=tf.id, ptf_id=i, chef_de_file=(i == payload.chef_de_file_id)))


@task_forces_router.get("", response_model=List[TaskForceRead])
async def lister_task_forces(
    ptf_id: Optional[int] = Query(None, description="Task forces dont ce PTF est membre"),
    tous: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    q = select(TaskForce).order_by(asc(TaskForce.ordre), asc(TaskForce.nom))
    est_staff = bool(current_user and (current_user.is_staff or current_user.is_superuser))
    if not (tous and est_staff):
        q = q.where(TaskForce.actif == True)  # noqa: E712
    if ptf_id:
        q = q.join(TaskForcePtf, TaskForcePtf.task_force_id == TaskForce.id).where(TaskForcePtf.ptf_id == ptf_id)
    return [await _lire(db, tf) for tf in (await db.execute(q)).scalars().all()]


@task_forces_router.get("/{slug}", response_model=TaskForceRead)
async def lire_task_force(slug: str, db: AsyncSession = Depends(get_db)):
    tf = (await db.execute(select(TaskForce).where(TaskForce.slug == slug))).scalar_one_or_none()
    if not tf or not tf.actif:
        raise HTTPException(status_code=404, detail="Task force introuvable.")
    return await _lire(db, tf)


@task_forces_router.post("", response_model=TaskForceRead, status_code=status.HTTP_201_CREATED)
async def creer_task_force(
    payload: TaskForceEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    slug = slugify.slugify(payload.nom)[:200]
    if (await db.execute(select(TaskForce.id).where(TaskForce.slug == slug))).first():
        raise HTTPException(status_code=409, detail="Une task force porte déjà ce nom.")
    tf = TaskForce(nom=payload.nom.strip(), slug=slug, thematique=payload.thematique.strip(),
                   description=(payload.description or "").strip() or None, ordre=payload.ordre, actif=payload.actif)
    db.add(tf)
    await db.flush()
    await _enregistrer_membres(db, tf, payload)
    await db.commit()
    await db.refresh(tf)
    return await _lire(db, tf)


@task_forces_router.put("/{task_force_id}", response_model=TaskForceRead)
async def modifier_task_force(
    task_force_id: int,
    payload: TaskForceEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    tf = await db.get(TaskForce, task_force_id)
    if not tf:
        raise HTTPException(status_code=404, detail="Task force introuvable.")
    slug = slugify.slugify(payload.nom)[:200]
    if slug != tf.slug and (await db.execute(select(TaskForce.id).where(TaskForce.slug == slug))).first():
        raise HTTPException(status_code=409, detail="Une task force porte déjà ce nom.")
    tf.nom, tf.slug = payload.nom.strip(), slug
    tf.thematique = payload.thematique.strip()
    tf.description = (payload.description or "").strip() or None
    tf.ordre, tf.actif = payload.ordre, payload.actif
    await _enregistrer_membres(db, tf, payload)
    await db.commit()
    await db.refresh(tf)
    return await _lire(db, tf)


@task_forces_router.delete("/{task_force_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_task_force(
    task_force_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    tf = await db.get(TaskForce, task_force_id)
    if not tf:
        raise HTTPException(status_code=404, detail="Task force introuvable.")
    await db.execute(delete(TaskForcePtf).where(TaskForcePtf.task_force_id == tf.id))
    await db.delete(tf)
    await db.commit()
