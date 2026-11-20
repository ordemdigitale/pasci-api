from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import desc, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_staff_user
from app.database.session import get_db
from app.models.journal import JournalAction
from app.models.users import User
from app.schemas.journal import ActionReferentiel, JournalActionRead, JournalPage
from app.services.journal import LIBELLES_ACTIONS, libelle_action

journal_router = APIRouter()


@journal_router.get("/actions", response_model=List[ActionReferentiel])
async def lister_types_actions(current_user: User = Depends(get_current_staff_user)):
    """Types d'actions enregistrés, pour alimenter le filtre de l'historique."""
    return [ActionReferentiel(code=code, libelle=libelle) for code, libelle in LIBELLES_ACTIONS.items()]


@journal_router.get("", response_model=JournalPage)
async def lister_historique(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None, description="Code d'action à filtrer"),
    cible_type: Optional[str] = Query(None, description="actualite, osc, offre, paiement…"),
    utilisateur: Optional[str] = Query(None, description="Recherche sur le nom ou l'email de l'auteur"),
    search: Optional[str] = Query(None, description="Recherche libre sur la cible et le détail"),
    depuis: Optional[date] = Query(None, description="Date de début (incluse)"),
    jusqu_a: Optional[date] = Query(None, description="Date de fin (incluse)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Historique des actions du back-office, de la plus récente à la plus ancienne."""
    conditions = []
    if action:
        conditions.append(JournalAction.action == action)
    if cible_type:
        conditions.append(JournalAction.cible_type == cible_type)
    if utilisateur:
        conditions.append(JournalAction.utilisateur.ilike(f"%{utilisateur.strip()}%"))
    if search:
        motif = f"%{search.strip()}%"
        conditions.append(
            or_(
                JournalAction.cible_libelle.ilike(motif),
                JournalAction.details.ilike(motif),
                JournalAction.utilisateur.ilike(motif),
            )
        )
    if depuis:
        conditions.append(JournalAction.created_at >= datetime.combine(depuis, time.min, tzinfo=timezone.utc))
    if jusqu_a:
        # Date de fin incluse : jusqu'à la fin de la journée
        conditions.append(
            JournalAction.created_at < datetime.combine(jusqu_a + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    total = (await db.execute(select(func.count(JournalAction.id)).where(*conditions))).scalar_one()
    result = await db.execute(
        select(JournalAction)
        .where(*conditions)
        .order_by(desc(JournalAction.created_at), desc(JournalAction.id))
        .offset((page - 1) * size)
        .limit(size)
    )
    items = [
        JournalActionRead.model_validate(ligne).model_copy(
            update={"action_libelle": libelle_action(ligne.action)}
        )
        for ligne in result.scalars().all()
    ]
    return JournalPage(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )
