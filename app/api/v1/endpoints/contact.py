from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.contact import ContactMessage
from app.models.users import User
from app.schemas.contact import ContactMessageCreate, ContactMessageRead, ContactMessageUpdate
from app.services.email import send_contact_accuse, send_contact_notif_admin
from app.core.auth import get_current_staff_user

contact_router = APIRouter()


@contact_router.post("", response_model=ContactMessageRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactMessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Soumettre un message de contact."""
    msg = ContactMessage(**data.model_dump())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Accusé de réception à l'expéditeur
    background_tasks.add_task(
        send_contact_accuse,
        nom=msg.nom,
        prenoms=msg.prenoms,
        email=msg.email,
        motif=msg.motif,
        categorie=msg.categorie_acteur,
        message=msg.message,
    )

    # Notification interne à l'équipe PASCI
    background_tasks.add_task(
        send_contact_notif_admin,
        nom=msg.nom,
        prenoms=msg.prenoms,
        email=msg.email,
        motif=msg.motif,
        categorie=msg.categorie_acteur,
        fonction=msg.fonction,
        contact=msg.contact,
        pays=msg.pays,
        lieu_residence=msg.lieu_residence,
        message=msg.message,
    )

    return msg


@contact_router.get("", response_model=List[ContactMessageRead], status_code=status.HTTP_200_OK)
async def get_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    statut: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Lister tous les messages de contact (staff only)."""
    query = select(ContactMessage).order_by(desc(ContactMessage.created_at))
    if statut:
        query = query.where(ContactMessage.statut == statut)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@contact_router.get("/{contact_id}", response_model=ContactMessageRead)
async def get_contact(contact_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == contact_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé.")
    return msg


@contact_router.patch("/{contact_id}", response_model=ContactMessageRead)
async def update_contact(contact_id: int, data: ContactMessageUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == contact_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(msg, key, value)
    await db.commit()
    await db.refresh(msg)
    return msg


@contact_router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == contact_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé.")
    await db.delete(msg)
    await db.commit()
