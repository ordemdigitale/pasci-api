from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.don import Don
from app.schemas.don import DonCreate, DonRead, DonInitierResponse, WebhookPayload
from app.services.cinetpay import cinetpay_service
from app.core.config import settings
from app.services.email import send_merci_don
from app.core.auth import get_current_staff_user
from app.models.users import User

dons_router = APIRouter()

DON_RETURN_URL = f"{settings.FRONTEND_URL}/faire-un-don/retour"
DON_FAILED_URL = f"{settings.FRONTEND_URL}/faire-un-don/retour?status=failed"
DON_NOTIFY_URL = f"{settings.API_BASE_URL}/api/v1/dons/webhook"


@dons_router.post("/initier", response_model=DonInitierResponse, status_code=status.HTTP_201_CREATED)
async def initier_don(data: DonCreate, db: AsyncSession = Depends(get_db)):
    """Crée un don et initie le paiement CinetPay."""
    if data.montant < 1000:
        raise HTTPException(status_code=400, detail="Le montant minimum est de 1 000 FCFA.")

    # Créer l'enregistrement en attente
    don = Don(
        nom=data.nom,
        email=data.email,
        telephone=data.telephone,
        montant=data.montant,
        message=data.message,
        statut="en_attente",
    )
    db.add(don)
    await db.commit()
    await db.refresh(don)

    # Initier le paiement CinetPay
    try:
        paiement = await cinetpay_service.initier_paiement(
            amount=data.montant,
            participant_name=data.nom,
            participant_email=data.email,
            description=f"Don PASCI — {data.montant} FCFA",
            formation_slug=f"don-{don.id}",
            participant_phone=data.telephone,
        )
    except Exception as e:
        await db.delete(don)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Erreur paiement: {str(e)}")

    don.transaction_id = paiement["transaction_id"]
    don.notify_token = paiement.get("notify_token", "")
    don.payment_url = paiement["payment_url"]
    await db.commit()
    await db.refresh(don)

    return DonInitierResponse(
        don_id=don.id,
        transaction_id=paiement["transaction_id"],
        payment_url=paiement["payment_url"],
        simulated=paiement.get("simulated", False),
    )


@dons_router.post("/webhook")
async def cinetpay_webhook_don(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook CinetPay — appelé automatiquement après chaque paiement de don."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    transaction_id = payload.get("transaction_id") or payload.get("cpm_trans_id")
    if not transaction_id:
        return {"status": "ignored"}

    result = await db.execute(select(Don).where(Don.transaction_id == transaction_id))
    don = result.scalar_one_or_none()
    if not don:
        return {"status": "not_found"}

    try:
        verification = await cinetpay_service.verifier_paiement(transaction_id)
        paiement_status = verification.get("status", "PENDING")
    except Exception:
        paiement_status = "PENDING"

    if paiement_status == "SUCCESS":
        don.statut = "success"
        await db.commit()
        await send_merci_don(
            donor_name=don.nom,
            donor_email=don.email,
            montant=don.montant,
            transaction_id=don.transaction_id,
        )
    elif paiement_status == "FAILED":
        don.statut = "failed"
        await db.commit()

    return {"status": "ok"}


@dons_router.post("/simulation/confirmer/{don_id}", response_model=DonRead)
async def simuler_don_confirme(don_id: int, db: AsyncSession = Depends(get_db)):
    """Simule un paiement accepté (mode dev sans CinetPay)."""
    if settings.cinetpay_configured:
        raise HTTPException(status_code=403, detail="Simulation désactivée en production.")
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")
    don.statut = "success"
    await db.commit()
    await db.refresh(don)
    await send_merci_don(
        donor_name=don.nom,
        donor_email=don.email,
        montant=don.montant,
        transaction_id=don.transaction_id,
    )
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
    query = select(Don).order_by(desc(Don.created_at)).offset(skip).limit(limit)
    if statut:
        query = select(Don).where(Don.statut == statut).order_by(desc(Don.created_at)).offset(skip).limit(limit)
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
async def delete_don(don_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Don).where(Don.id == don_id))
    don = result.scalar_one_or_none()
    if not don:
        raise HTTPException(status_code=404, detail="Don non trouvé.")
    await db.delete(don)
    await db.commit()
