# api/v1/endpoints/adhesion.py
import secrets
import string
import slugify as python_slugify

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.models.adhesion import DemandeAdhesion
from app.models.crasc import Osc, Crasc
from app.models.users import User
from app.schemas.adhesion import (
    DemandeAdhesionCreate,
    DemandeAdhesionRead,
    DemandeAdhesionUpdate,
    DemandeAdhesionReadWithCredentials,
    OscCredentials,
)

adhesion_router = APIRouter()


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _provision_osc_and_user(demande: DemandeAdhesion, db: AsyncSession) -> Optional[OscCredentials]:
    """
    Crée (ou retrouve) l'OSC correspondant à la demande, puis crée
    (ou met à jour) le compte utilisateur lié.
    Retourne les credentials à afficher à l'administrateur.
    """
    # --- 1. Trouver le CRASC par nom ---
    crasc_id: Optional[int] = None
    if demande.crasc_nom:
        crasc_result = await db.execute(
            select(Crasc).where(Crasc.name.ilike(f"%{demande.crasc_nom}%"))
        )
        crasc = crasc_result.scalar_one_or_none()
        if crasc:
            crasc_id = crasc.id

    # --- 2. Créer ou retrouver l'OSC ---
    osc_result = await db.execute(
        select(Osc).where(Osc.name == demande.nom_organisation)
    )
    osc = osc_result.scalar_one_or_none()

    if not osc:
        osc = Osc(
            name=demande.nom_organisation,
            description=demande.description,
            email=demande.email,
            phone=demande.telephone,
            ville=demande.ville,
            crasc_id=crasc_id,
        )
        db.add(osc)
        await db.flush()  # obtenir l'id sans commit

    # --- 3. Créer ou mettre à jour l'utilisateur ---
    user_result = await db.execute(
        select(User).where(User.email == demande.email)
    )
    user = user_result.scalar_one_or_none()

    temp_password = _generate_password()
    base_username = python_slugify.slugify(demande.nom_organisation)[:30]

    if user:
        # Lier l'utilisateur existant à l'OSC
        user.osc_id = osc.id
        credentials = OscCredentials(
            osc_id=osc.id,
            osc_name=osc.name,
            email=user.email,
            username=user.username or user.email,
            temp_password="(compte existant — mot de passe inchangé)",
        )
    else:
        # S'assurer que le username est unique
        username = base_username
        counter = 1
        while True:
            existing = await db.execute(select(User).where(User.username == username))
            if not existing.scalar_one_or_none():
                break
            username = f"{base_username}-{counter}"
            counter += 1

        user = User(
            email=demande.email,
            username=username,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            is_redacteur=False,
            osc_id=osc.id,
        )
        user.set_password(temp_password)
        db.add(user)

        credentials = OscCredentials(
            osc_id=osc.id,
            osc_name=osc.name,
            email=demande.email,
            username=username,
            temp_password=temp_password,
        )

    await db.commit()
    await db.refresh(osc)
    return credentials


@adhesion_router.post("", response_model=DemandeAdhesionRead, status_code=status.HTTP_201_CREATED)
async def create_demande(data: DemandeAdhesionCreate, db: AsyncSession = Depends(get_db)):
    """Soumettre une nouvelle demande d'adhésion"""
    demande = DemandeAdhesion(**data.model_dump())
    db.add(demande)
    await db.commit()
    await db.refresh(demande)
    return demande


@adhesion_router.get("", response_model=List[DemandeAdhesionRead], status_code=status.HTTP_200_OK)
async def get_demandes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    statut: Optional[str] = Query(None, description="Filtrer par statut: en_attente, approuvee, rejetee"),
    db: AsyncSession = Depends(get_db),
):
    """Lister toutes les demandes d'adhésion"""
    query = select(DemandeAdhesion).order_by(desc(DemandeAdhesion.created_at)).offset(skip).limit(limit)
    if statut:
        query = select(DemandeAdhesion).where(DemandeAdhesion.statut == statut).order_by(desc(DemandeAdhesion.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@adhesion_router.get("/{demande_id}", response_model=DemandeAdhesionRead, status_code=status.HTTP_200_OK)
async def get_demande(demande_id: int, db: AsyncSession = Depends(get_db)):
    """Obtenir une demande d'adhésion par ID"""
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    return demande


@adhesion_router.patch("/{demande_id}", response_model=DemandeAdhesionReadWithCredentials, status_code=status.HTTP_200_OK)
async def update_demande(demande_id: int, data: DemandeAdhesionUpdate, db: AsyncSession = Depends(get_db)):
    """
    Mettre à jour le statut d'une demande (approuver / rejeter).
    Lors de l'approbation, crée automatiquement l'OSC et le compte utilisateur associé.
    """
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")

    previous_statut = demande.statut
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(demande, key, value)
    await db.commit()
    await db.refresh(demande)

    # Provisionner OSC + utilisateur uniquement lors du passage à "approuvee"
    credentials: Optional[OscCredentials] = None
    if demande.statut == "approuvee" and previous_statut != "approuvee":
        try:
            credentials = await _provision_osc_and_user(demande, db)
        except Exception as e:
            # Ne pas bloquer l'approbation si la création échoue
            import traceback
            traceback.print_exc()

    response_data = demande.__dict__.copy()
    response_data["credentials"] = credentials
    return DemandeAdhesionReadWithCredentials(**{
        k: v for k, v in response_data.items() if not k.startswith("_")
    })


@adhesion_router.delete("/{demande_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demande(demande_id: int, db: AsyncSession = Depends(get_db)):
    """Supprimer une demande d'adhésion"""
    result = await db.execute(select(DemandeAdhesion).where(DemandeAdhesion.id == demande_id))
    demande = result.scalar_one_or_none()
    if not demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande non trouvée.")
    await db.delete(demande)
    await db.commit()
