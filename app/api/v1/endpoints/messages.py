# api/v1/endpoints/messages.py | Messages adressés à une sélection d'OSC ou de PTF
import json
import logging
from typing import List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlmodel import desc, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_staff_user
from app.database.session import get_db
from app.models.crasc import Crasc, Osc, OscType, Region
from app.models.forum import PoleConcertation
from app.models.message_groupe import MessageGroupe
from app.models.notification import Notification
from app.models.ptf import Ptf
from app.models.task_force import TaskForce, TaskForcePtf
from app.models.users import User
from app.schemas.message_groupe import (
    ApercuDestinataires,
    CriteresDestinataires,
    CriteresDisponibles,
    DestinataireApercu,
    MessageGroupeCreate,
    MessageGroupeRead,
    OptionCritere,
)
from app.services.email import send_message_groupe
from app.services.journal import journaliser
from app.services.osc_etiquettes import CATEGORIES, filtre_categorie
from app.services.recherche import egal

logger = logging.getLogger(__name__)
messages_router = APIRouter()

APERCU_MAX = 25


def _criteres_renseignes(criteres: CriteresDestinataires) -> bool:
    return bool(
        criteres.crasc_ids or criteres.type_osc_ids or criteres.categories
        or criteres.regions or criteres.pole_ids or criteres.task_force_ids
        or criteres.toutes_les_osc
    )


async def _oscs_ciblees(db: AsyncSession, criteres: CriteresDestinataires) -> List[Osc]:
    """OSC correspondant aux critères (ET entre critères, OU à l'intérieur)."""
    vise_osc = bool(
        criteres.toutes_les_osc or criteres.crasc_ids or criteres.type_osc_ids
        or criteres.categories or criteres.regions or criteres.pole_ids
    )
    if not vise_osc:
        return []

    conditions = [Osc.statut_publication == "publie", Osc.is_visible == True]  # noqa: E712
    if criteres.crasc_ids:
        conditions.append(Osc.crasc_id.in_(criteres.crasc_ids))
    if criteres.type_osc_ids:
        conditions.append(Osc.type_id.in_(criteres.type_osc_ids))
    if criteres.categories:
        conditions.append(or_(*[filtre_categorie(Osc.categorie, c) for c in criteres.categories]))
    if criteres.regions:
        conditions.append(or_(*[egal(Osc.region_nom, r) for r in criteres.regions]))
    if criteres.pole_ids:
        conditions.append(Osc.poles.any(PoleConcertation.id.in_(criteres.pole_ids)))

    result = await db.execute(
        select(Osc).options(selectinload(Osc.poles)).where(*conditions).order_by(Osc.name)
    )
    return list(result.scalars().unique().all())


async def _ptfs_ciblees(db: AsyncSession, criteres: CriteresDestinataires) -> List[Ptf]:
    """PTF membres des task forces sélectionnées."""
    if not criteres.task_force_ids:
        return []
    result = await db.execute(
        select(Ptf)
        .join(TaskForcePtf, TaskForcePtf.ptf_id == Ptf.id)
        .where(TaskForcePtf.task_force_id.in_(criteres.task_force_ids))
        .order_by(Ptf.name)
    )
    return list(result.scalars().unique().all())


async def _comptes_des_oscs(db: AsyncSession, osc_ids: List[int]) -> dict:
    """Comptes utilisateurs actifs rattachés aux OSC visées (osc_id → User)."""
    if not osc_ids:
        return {}
    result = await db.execute(
        select(User).where(User.osc_id.in_(osc_ids), User.is_active == True)  # noqa: E712
    )
    comptes = {}
    for utilisateur in result.scalars().all():
        comptes.setdefault(utilisateur.osc_id, utilisateur)
    return comptes


async def _resoudre(
    db: AsyncSession, criteres: CriteresDestinataires
) -> Tuple[List[DestinataireApercu], List[Tuple[str, str]], List[User]]:
    """Destinataires, couples (nom, email) à écrire et comptes à notifier."""
    oscs = await _oscs_ciblees(db, criteres)
    ptfs = await _ptfs_ciblees(db, criteres)
    comptes = await _comptes_des_oscs(db, [o.id for o in oscs])

    destinataires: List[DestinataireApercu] = []
    emails: List[Tuple[str, str]] = []
    a_notifier: List[User] = []

    for osc in oscs:
        compte = comptes.get(osc.id)
        email = (osc.email or (compte.email if compte else "") or "").strip()
        destinataires.append(
            DestinataireApercu(nom=osc.name, email=email or None, type="osc", a_un_compte=compte is not None)
        )
        if email:
            emails.append((osc.name, email))
        if compte:
            a_notifier.append(compte)

    for ptf in ptfs:
        email = (ptf.email or "").strip()
        destinataires.append(
            DestinataireApercu(nom=ptf.name, email=email or None, type="ptf", a_un_compte=False)
        )
        if email:
            emails.append((ptf.name, email))

    return destinataires, emails, a_notifier


@messages_router.get("/criteres", response_model=CriteresDisponibles)
async def criteres_disponibles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Valeurs sélectionnables et nombre d'OSC publiées derrière chacune."""
    publiees = (Osc.statut_publication == "publie", Osc.is_visible == True)  # noqa: E712

    async def compter(colonne) -> dict:
        result = await db.execute(
            select(colonne, func.count(Osc.id)).where(*publiees).group_by(colonne)
        )
        return {cle: nb for cle, nb in result.all() if cle is not None}

    par_crasc = await compter(Osc.crasc_id)
    par_type = await compter(Osc.type_id)
    par_region = await compter(Osc.region_nom)

    crascs = (await db.execute(select(Crasc).order_by(Crasc.name))).scalars().all()
    types = (await db.execute(select(OscType).order_by(OscType.name))).scalars().all()
    poles = (await db.execute(select(PoleConcertation).order_by(PoleConcertation.name))).scalars().all()
    task_forces = (await db.execute(select(TaskForce).where(TaskForce.actif == True).order_by(TaskForce.nom))).scalars().all()  # noqa: E712
    regions = (await db.execute(select(Region).order_by(Region.name))).scalars().all()

    categories = []
    for code, (sigle, libelle, _) in CATEGORIES.items():
        nb = (await db.execute(
            select(func.count(Osc.id)).where(*publiees, filtre_categorie(Osc.categorie, code))
        )).scalar_one()
        categories.append(OptionCritere(valeur=code, libelle=f"{libelle} ({sigle})", nombre=nb))

    async def nb_osc_pole(pole_id: int) -> int:
        return (await db.execute(
            select(func.count(Osc.id)).where(*publiees, Osc.poles.any(PoleConcertation.id == pole_id))
        )).scalar_one()

    return CriteresDisponibles(
        crasc=[OptionCritere(valeur=str(c.id), libelle=c.name, nombre=par_crasc.get(c.id, 0)) for c in crascs],
        types_osc=[OptionCritere(valeur=str(t.id), libelle=t.name, nombre=par_type.get(t.id, 0)) for t in types],
        categories=categories,
        regions=[OptionCritere(valeur=r.name, libelle=r.name, nombre=par_region.get(r.name, 0)) for r in regions],
        poles=[OptionCritere(valeur=str(p.id), libelle=p.name, nombre=await nb_osc_pole(p.id)) for p in poles],
        task_forces=[OptionCritere(valeur=str(tf.id), libelle=tf.nom) for tf in task_forces],
    )


@messages_router.post("/destinataires", response_model=ApercuDestinataires)
async def previsualiser_destinataires(
    criteres: CriteresDestinataires,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Qui recevra le message, avant de l'envoyer."""
    if not _criteres_renseignes(criteres):
        raise HTTPException(status_code=400, detail="Sélectionnez au moins un critère de destinataires.")
    destinataires, emails, a_notifier = await _resoudre(db, criteres)
    return ApercuDestinataires(
        total=len(destinataires),
        avec_email=len(emails),
        avec_compte=len(a_notifier),
        sans_email=sum(1 for d in destinataires if not d.email),
        apercu=destinataires[:APERCU_MAX],
    )


@messages_router.post("", response_model=MessageGroupeRead, status_code=status.HTTP_201_CREATED)
async def envoyer_message_groupe(
    data: MessageGroupeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Envoyer un message à la sélection : email + notification dans la plateforme."""
    if not _criteres_renseignes(data.criteres):
        raise HTTPException(status_code=400, detail="Sélectionnez au moins un critère de destinataires.")

    destinataires, emails, a_notifier = await _resoudre(db, data.criteres)
    if not destinataires:
        raise HTTPException(status_code=404, detail="Aucun destinataire ne correspond à cette sélection.")

    auteur_nom = current_user.full_name or current_user.username or current_user.email

    for compte in a_notifier:
        db.add(
            Notification(
                user_id=compte.id,
                title=data.objet,
                message=data.message,
                type="message",
                link_url=data.lien,
            )
        )

    envoi = MessageGroupe(
        objet=data.objet.strip(),
        message=data.message.strip(),
        criteres=json.dumps(data.criteres.model_dump(), ensure_ascii=False),
        lien=data.lien,
        nb_destinataires=len(destinataires),
        nb_emails=len(emails),
        nb_notifications=len(a_notifier),
        auteur_id=current_user.id,
        auteur_nom=auteur_nom,
    )
    db.add(envoi)
    await db.commit()
    await db.refresh(envoi)

    for nom, email in emails:
        background_tasks.add_task(
            send_message_groupe,
            destinataire=email,
            nom_destinataire=nom,
            objet=envoi.objet,
            message=envoi.message,
            lien=envoi.lien,
            auteur=auteur_nom,
        )

    await journaliser(
        db, current_user, action="message_groupe_envoye",
        cible_type="message", cible_id=str(envoi.id), cible_libelle=envoi.objet,
        details=f"{len(destinataires)} destinataire(s) · {len(emails)} email(s) · {len(a_notifier)} notification(s)",
    )

    return envoi


@messages_router.get("", response_model=List[MessageGroupeRead])
async def historique_messages(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Messages groupés déjà envoyés, du plus récent au plus ancien."""
    result = await db.execute(
        select(MessageGroupe).order_by(desc(MessageGroupe.created_at)).limit(limit)
    )
    return result.scalars().all()
