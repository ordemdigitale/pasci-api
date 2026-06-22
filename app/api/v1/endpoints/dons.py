from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.don import Don
from app.schemas.don import DonCreate, DonRead, DonCreateResponse, DonSoumettreTransaction
from app.services.email import send_merci_don, send_don_instructions, send_don_soumis_admin
from app.core.auth import get_current_staff_user
from app.models.users import User

dons_router = APIRouter()


@dons_router.post("/creer", response_model=DonCreateResponse, status_code=status.HTTP_201_CREATED)
async def creer_don(
    data: DonCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Crée un don et envoie les instructions de paiement Wave/OM au donateur."""
    if data.montant < 1000:
        raise HTTPException(status_code=400, detail="Le montant minimum est de 1 000 FCFA.")

    don = Don(
        nom=data.nom,
        prenoms=data.prenoms,
        fonction=data.fonction,
        sexe=data.sexe,
        tranche_age=data.tranche_age,
        email=data.email,
        telephone=data.telephone,
        pays=data.pays,
        lieu_residence=data.lieu_residence,
        montant=data.montant,
        message=data.message,
        statut="en_attente",
    )
    db.add(don)
    await db.commit()
    await db.refresh(don)

    donor_name = f"{data.prenoms or ''} {data.nom}".strip()
    background_tasks.add_task(
        send_don_instructions,
        donor_name=donor_name,
        donor_email=data.email,
        montant=data.montant,
        don_id=don.id,
    )

    return DonCreateResponse(don_id=don.id, statut=don.statut)


@dons_router.post("/{don_id}/soumettre-paiement", response_model=DonRead)
async def soumettre_paiement_don(
    don_id: int,
    data: DonSoumettreTransaction,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Soumettre le code de transaction Wave/OM pour un don."""
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")
    if don.statut not in ("en_attente",):
        raise HTTPException(
            status_code=400,
            detail=f"Ce don ne peut pas être soumis (statut actuel : {don.statut})."
        )

    don.transaction_id = data.transaction_id
    don.operateur = data.operateur
    don.statut = "soumis"
    await db.commit()
    await db.refresh(don)

    donor_name = f"{don.prenoms or ''} {don.nom}".strip()
    background_tasks.add_task(
        send_don_soumis_admin,
        donor_name=donor_name,
        donor_email=don.email,
        montant=don.montant,
        transaction_id=data.transaction_id,
        don_id=don.id,
    )

    return don


@dons_router.patch("/{don_id}/confirmer", response_model=DonRead)
async def confirmer_don(
    don_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Confirmer un don (admin) — envoie l'email de remerciement."""
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")

    don.statut = "success"
    await db.commit()
    await db.refresh(don)

    donor_name = f"{don.prenoms or ''} {don.nom}".strip()
    background_tasks.add_task(
        send_merci_don,
        donor_name=donor_name,
        donor_email=don.email,
        montant=don.montant,
        transaction_id=don.transaction_id,
    )

    return don


@dons_router.patch("/{don_id}/rejeter", response_model=DonRead)
async def rejeter_don(
    don_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Rejeter un don (admin)."""
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")

    don.statut = "rejete"
    await db.commit()
    await db.refresh(don)
    return don


@dons_router.get("", response_model=List[DonRead], status_code=status.HTTP_200_OK)
async def get_dons(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    statut: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Lister tous les dons (admin)."""
    if statut:
        query = select(Don).where(Don.statut == statut).order_by(desc(Don.created_at)).offset(skip).limit(limit)
    else:
        query = select(Don).order_by(desc(Don.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@dons_router.get("/{don_id}", response_model=DonRead)
async def get_don(
    don_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")
    return don


@dons_router.delete("/{don_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_don(
    don_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")
    await db.delete(don)
    await db.commit()
