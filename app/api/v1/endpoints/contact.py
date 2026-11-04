from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.core.config import settings
from app.models.contact import ContactMessage, ContactReponse
from app.models.site_config import SiteConfig
from app.models.users import User
from app.schemas.contact import (
    ContactEmailsRead,
    ContactEmailsUpdate,
    ContactMessageCreate,
    ContactMessageDetail,
    ContactMessageRead,
    ContactMessageUpdate,
    ContactReponseCreate,
    ContactReponseRead,
)
from app.services.email import (
    send_contact_accuse,
    send_contact_notif_admin,
    send_contact_reponse,
)
from app.core.auth import get_current_staff_user, get_current_superuser

contact_router = APIRouter()

# Clé de configuration : boîtes mails qui reçoivent les nouveaux messages
CLE_EMAILS_NOTIF = "contact_notification_emails"


async def _emails_notification(db: AsyncSession) -> List[str]:
    """Destinataires des notifications de contact.

    Configurés dans le backoffice (liste séparée par des virgules) ; à défaut on
    retombe sur ADMIN_EMAIL. Sans cette configuration les messages partaient vers
    SMTP_FROM (noreply@…) et n'arrivaient dans aucune boîte réelle.
    """
    result = await db.execute(select(SiteConfig).where(SiteConfig.key == CLE_EMAILS_NOTIF))
    row = result.scalars().first()
    emails = [e.strip() for e in (row.value or "").split(",") if e.strip()] if row else []
    return emails or [settings.ADMIN_EMAIL]


async def _get_message_ou_404(db: AsyncSession, contact_id: int) -> ContactMessage:
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == contact_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé.")
    return msg


async def _reponses(db: AsyncSession, contact_id: int) -> List[ContactReponse]:
    result = await db.execute(
        select(ContactReponse)
        .where(ContactReponse.contact_id == contact_id)
        .order_by(ContactReponse.created_at.asc())
    )
    return list(result.scalars().all())


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

    destinataires = await _emails_notification(db)

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
        destinataires=destinataires,
    )

    return msg


@contact_router.get("", response_model=List[ContactMessageRead], status_code=status.HTTP_200_OK)
async def get_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    statut: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Lister tous les messages de contact (staff only)."""
    query = select(ContactMessage).order_by(desc(ContactMessage.created_at))
    if statut:
        query = query.where(ContactMessage.statut == statut)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@contact_router.get("/emails-notification", response_model=ContactEmailsRead)
async def get_emails_notification(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Boîtes mails qui reçoivent les nouveaux messages de contact (staff only)."""
    return ContactEmailsRead(emails=await _emails_notification(db))


@contact_router.put("/emails-notification", response_model=ContactEmailsRead)
async def set_emails_notification(
    data: ContactEmailsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Définir les boîtes mails destinataires des notifications (staff only)."""
    emails = [e.strip() for e in data.emails if e and e.strip()]
    for email in emails:
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise HTTPException(status_code=422, detail=f"Adresse email invalide : {email}")

    result = await db.execute(select(SiteConfig).where(SiteConfig.key == CLE_EMAILS_NOTIF))
    row = result.scalars().first()
    valeur = ", ".join(emails)
    if row:
        row.value = valeur
    else:
        db.add(SiteConfig(key=CLE_EMAILS_NOTIF, value=valeur))
    await db.commit()
    return ContactEmailsRead(emails=emails or [settings.ADMIN_EMAIL])


@contact_router.get("/{contact_id}", response_model=ContactMessageDetail)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    msg = await _get_message_ou_404(db, contact_id)
    detail = ContactMessageDetail.model_validate(msg)
    detail.reponses = [ContactReponseRead.model_validate(r) for r in await _reponses(db, contact_id)]
    return detail


@contact_router.get("/{contact_id}/reponses", response_model=List[ContactReponseRead])
async def list_reponses(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    await _get_message_ou_404(db, contact_id)
    return await _reponses(db, contact_id)


@contact_router.post(
    "/{contact_id}/reponses",
    response_model=ContactReponseRead,
    status_code=status.HTTP_201_CREATED,
)
async def repondre_contact(
    contact_id: int,
    data: ContactReponseCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Répondre directement à un message depuis le backoffice (staff only).

    La réponse part par email à l'usager, avec en Reply-To l'adresse de
    l'administrateur pour poursuivre l'échange, et reste historisée ici.
    """
    msg = await _get_message_ou_404(db, contact_id)

    auteur_nom = current_user.full_name or current_user.username or current_user.email

    reponse = ContactReponse(
        contact_id=msg.id,
        message=data.message.strip(),
        auteur_id=current_user.id,
        auteur_nom=auteur_nom,
        auteur_email=current_user.email,
    )
    db.add(reponse)

    # Un message auquel on a répondu est considéré comme traité
    msg.statut = "traite"
    await db.commit()
    await db.refresh(reponse)

    background_tasks.add_task(
        send_contact_reponse,
        nom=msg.nom,
        prenoms=msg.prenoms,
        email=msg.email,
        motif=msg.motif,
        reponse=reponse.message,
        message_initial=msg.message,
        auteur=auteur_nom,
        reply_to=str(data.reply_to) if data.reply_to else current_user.email,
    )

    return reponse


@contact_router.patch("/{contact_id}", response_model=ContactMessageRead)
async def update_contact(
    contact_id: int,
    data: ContactMessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    msg = await _get_message_ou_404(db, contact_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(msg, key, value)
    await db.commit()
    await db.refresh(msg)
    return msg


@contact_router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    msg = await _get_message_ou_404(db, contact_id)
    await db.delete(msg)
    await db.commit()
