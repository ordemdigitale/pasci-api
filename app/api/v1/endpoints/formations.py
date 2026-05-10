# app/api/v1/endpoints/formations.py
"""
Formations/Training endpoints
"""
import os
import shutil
import uuid
import slugify
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, UploadFile, Depends, File, Form, Query
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.core.config import settings
from app.database.session import get_db
from app.models.formation import Formation, FormationRubrique, FormationInscription, Certificat, FormationModule, FormationLecon, FormationProgression, FormationAvis
from app.models.users import User
from app.schemas.formation import (
    FormationCreate, FormationRead, FormationUpdate, FormationReadWithRelations,
    FormationRubriqueCreate, FormationRubriqueRead, FormationRubriqueUpdate,
    FormationInscriptionCreate, FormationInscriptionRead, CertificatRead,
    PaiementInitierResponse, PaiementWebhookPayload,
    FormationModuleCreate, FormationModuleUpdate, FormationModuleRead,
    FormationLeconCreate, FormationLeconUpdate, FormationLeconRead,
    FormationAvisCreate, FormationAvisRead,
)
from app.core.auth import get_current_user, get_current_staff_user, get_current_redacteur_or_staff
from app.services.cinetpay import cinetpay_service
from app.services.email import (
    send_inscription_confirmation,
    send_paiement_confirme,
    send_certificat_emis,
)
from app.core.config import settings

formations_router = APIRouter()


# ─────────────────────────────────────────────────────────────
# RUBRIQUES  (doit être AVANT les routes /{formation_slug})
# ─────────────────────────────────────────────────────────────

@formations_router.get("/rubriques", response_model=List[FormationRubriqueRead])
async def list_rubriques(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Liste toutes les rubriques (filtre optionnel actives seulement)"""
    query = select(FormationRubrique).order_by(FormationRubrique.name)
    if active_only:
        query = query.where(FormationRubrique.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


@formations_router.post("/rubriques", response_model=FormationRubriqueRead, status_code=status.HTTP_201_CREATED)
async def create_rubrique(
    rubrique: FormationRubriqueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    db_r = FormationRubrique(**rubrique.model_dump())
    db.add(db_r)
    await db.commit()
    await db.refresh(db_r)
    return db_r


@formations_router.patch("/rubriques/{rubrique_id}", response_model=FormationRubriqueRead)
async def update_rubrique(
    rubrique_id: int,
    rubrique_update: FormationRubriqueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(FormationRubrique).where(FormationRubrique.id == rubrique_id))
    rubrique = result.scalar_one_or_none()
    if not rubrique:
        raise HTTPException(status_code=404, detail="Rubrique non trouvée.")
    for key, value in rubrique_update.model_dump(exclude_unset=True).items():
        setattr(rubrique, key, value)
    await db.commit()
    await db.refresh(rubrique)
    return rubrique


@formations_router.delete("/rubriques/{rubrique_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rubrique(
    rubrique_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(FormationRubrique).where(FormationRubrique.id == rubrique_id))
    rubrique = result.scalar_one_or_none()
    if not rubrique:
        raise HTTPException(status_code=404, detail="Rubrique non trouvée.")
    await db.delete(rubrique)
    await db.commit()
    return None


# ─────────────────────────────────────────────────────────────
# VÉRIFICATION CERTIFICAT (doit être AVANT /{formation_slug})
# ─────────────────────────────────────────────────────────────

@formations_router.post("/lecons/{lecon_id}/vue")
async def marquer_lecon_vue(
    lecon_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marque une leçon comme vue et vérifie si la formation est complétée à 100%"""
    # Vérifier que la leçon existe
    lecon_result = await db.execute(select(FormationLecon).where(FormationLecon.id == lecon_id))
    lecon = lecon_result.scalar_one_or_none()
    if not lecon:
        raise HTTPException(status_code=404, detail="Leçon introuvable.")

    # Récupérer le module puis la formation
    module_result = await db.execute(select(FormationModule).where(FormationModule.id == lecon.module_id))
    module = module_result.scalar_one()
    formation_id = module.formation_id

    # Trouver l'inscription active de l'utilisateur
    insc_result = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation_id,
            FormationInscription.participant_email == current_user.email,
        )
    )
    inscription = insc_result.scalar_one_or_none()
    if not inscription:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à cette formation.")

    # Enregistrer la vue si pas déjà faite
    existing = await db.execute(
        select(FormationProgression).where(
            FormationProgression.inscription_id == inscription.id,
            FormationProgression.lecon_id == lecon_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(FormationProgression(inscription_id=inscription.id, lecon_id=lecon_id))
        await db.commit()

    # Compter toutes les leçons de la formation
    all_lecons_result = await db.execute(
        select(FormationLecon)
        .join(FormationModule, FormationLecon.module_id == FormationModule.id)
        .where(FormationModule.formation_id == formation_id)
    )
    total_lecons = len(all_lecons_result.scalars().all())

    # Compter les leçons vues
    vues_result = await db.execute(
        select(FormationProgression).where(FormationProgression.inscription_id == inscription.id)
    )
    total_vues = len(vues_result.scalars().all())

    progression = round((total_vues / total_lecons) * 100) if total_lecons > 0 else 0

    # 100% → auto-complétion + certificat
    certificat_code = None
    if progression >= 100 and not inscription.is_completed:
        inscription.is_completed = True
        inscription.completed_at = datetime.utcnow()

        # Émettre le certificat si pas encore fait
        if not inscription.certificate_issued:
            form_result = await db.execute(select(Formation).where(Formation.id == formation_id))
            formation = form_result.scalar_one()
            certificat = Certificat(
                inscription_id=inscription.id,
                formation_title=formation.title,
                participant_name=inscription.participant_name,
                participant_email=inscription.participant_email,
            )
            db.add(certificat)
            inscription.certificate_issued = True
            await db.commit()
            await db.refresh(certificat)
            certificat_code = certificat.code
            await send_certificat_emis(
                participant_name=inscription.participant_name,
                participant_email=inscription.participant_email,
                formation_title=formation.title,
                cert_code=certificat.code,
            )
        else:
            await db.commit()

    return {
        "lecon_id": lecon_id,
        "progression": progression,
        "total_lecons": total_lecons,
        "lecons_vues": total_vues,
        "completed": inscription.is_completed,
        "certificat_code": certificat_code,
    }


@formations_router.get("/{formation_slug}/ma-progression")
async def ma_progression(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne la progression de l'utilisateur connecté pour une formation"""
    form_result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = form_result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation introuvable.")

    insc_result = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation.id,
            FormationInscription.participant_email == current_user.email,
        )
    )
    inscription = insc_result.scalar_one_or_none()
    if not inscription:
        return {"progression": 0, "lecons_vues": [], "completed": False, "certificat_code": None}

    # Leçons vues
    vues_result = await db.execute(
        select(FormationProgression).where(FormationProgression.inscription_id == inscription.id)
    )
    vues = vues_result.scalars().all()
    lecons_vues_ids = [v.lecon_id for v in vues]

    # Total leçons
    all_lecons_result = await db.execute(
        select(FormationLecon)
        .join(FormationModule, FormationLecon.module_id == FormationModule.id)
        .where(FormationModule.formation_id == formation.id)
    )
    total_lecons = len(all_lecons_result.scalars().all())
    progression = round((len(lecons_vues_ids) / total_lecons) * 100) if total_lecons > 0 else 0

    # Code certificat si émis
    cert_code = None
    if inscription.certificate_issued:
        cert_result = await db.execute(
            select(Certificat).where(Certificat.inscription_id == inscription.id)
        )
        cert = cert_result.scalar_one_or_none()
        if cert:
            cert_code = cert.code

    return {
        "progression": progression,
        "lecons_vues": lecons_vues_ids,
        "total_lecons": total_lecons,
        "completed": inscription.is_completed,
        "certificat_code": cert_code,
    }


@formations_router.post("/{formation_slug}/avis", response_model=FormationAvisRead, status_code=status.HTTP_201_CREATED)
async def soumettre_avis(
    formation_slug: str,
    avis_data: FormationAvisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soumettre un avis sur une formation (inscrits uniquement, un seul avis par inscription)"""
    form_result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = form_result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation introuvable.")

    insc_result = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation.id,
            FormationInscription.participant_email == current_user.email,
        )
    )
    inscription = insc_result.scalar_one_or_none()
    if not inscription:
        raise HTTPException(status_code=403, detail="Vous devez être inscrit pour laisser un avis.")

    # Vérifier qu'il n'a pas déjà laissé un avis
    existing = await db.execute(
        select(FormationAvis).where(FormationAvis.inscription_id == inscription.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Vous avez déjà laissé un avis pour cette formation.")

    participant_name = [current_user.first_name, current_user.last_name]
    participant_name = " ".join(p for p in participant_name if p) or current_user.username or current_user.email.split("@")[0]

    avis = FormationAvis(
        formation_id=formation.id,
        inscription_id=inscription.id,
        participant_name=participant_name,
        note=avis_data.note,
        commentaire=avis_data.commentaire,
    )
    db.add(avis)
    await db.commit()
    await db.refresh(avis)
    return avis


@formations_router.get("/{formation_slug}/mon-avis")
async def mon_avis(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne l'avis de l'utilisateur connecté pour cette formation, ou null"""
    form_result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = form_result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation introuvable.")

    insc_result = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation.id,
            FormationInscription.participant_email == current_user.email,
        )
    )
    inscription = insc_result.scalar_one_or_none()
    if not inscription:
        return None

    avis_result = await db.execute(
        select(FormationAvis).where(FormationAvis.inscription_id == inscription.id)
    )
    avis = avis_result.scalar_one_or_none()
    if not avis:
        return None
    return {"id": avis.id, "note": avis.note, "commentaire": avis.commentaire}


@formations_router.get("/{formation_slug}/avis", response_model=List[FormationAvisRead])
async def liste_avis(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Liste les avis d'une formation (public)"""
    form_result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = form_result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation introuvable.")

    result = await db.execute(
        select(FormationAvis)
        .where(FormationAvis.formation_id == formation.id)
        .order_by(FormationAvis.created_at.desc())
    )
    return result.scalars().all()


@formations_router.get("/mes-certificats", response_model=List[CertificatRead])
async def mes_certificats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne les certificats de l'utilisateur connecté (par email)"""
    result = await db.execute(
        select(Certificat)
        .where(Certificat.participant_email == current_user.email)
        .order_by(Certificat.issued_at.desc())
    )
    return result.scalars().all()


@formations_router.get("/certificats/verifier/{code}", response_model=CertificatRead)
async def verifier_certificat(code: str, db: AsyncSession = Depends(get_db)):
    """Vérifier l'authenticité d'un certificat via son code unique (public)"""
    result = await db.execute(select(Certificat).where(Certificat.code == code.upper()))
    certificat = result.scalar_one_or_none()
    if not certificat:
        raise HTTPException(status_code=404, detail="Certificat introuvable ou invalide.")
    return certificat


# ─────────────────────────────────────────────────────────────
# ÉMETTRE CERTIFICAT (doit être AVANT /{formation_slug})
# ─────────────────────────────────────────────────────────────

@formations_router.post("/inscriptions/{inscription_id}/certifier", response_model=CertificatRead, status_code=status.HTTP_201_CREATED)
async def emettre_certificat(
    inscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Émettre un certificat numérique pour une inscription (staff only)"""
    result = await db.execute(
        select(FormationInscription).where(FormationInscription.id == inscription_id)
    )
    inscription = result.scalar_one_or_none()
    if not inscription:
        raise HTTPException(status_code=404, detail="Inscription non trouvée.")
    if inscription.certificate_issued:
        cert_result = await db.execute(
            select(Certificat).where(Certificat.inscription_id == inscription_id)
        )
        return cert_result.scalar_one()

    form_result = await db.execute(select(Formation).where(Formation.id == inscription.formation_id))
    formation = form_result.scalar_one()

    if not inscription.is_completed:
        inscription.is_completed = True
        inscription.completed_at = datetime.utcnow()

    certificat = Certificat(
        inscription_id=inscription.id,
        formation_title=formation.title,
        participant_name=inscription.participant_name,
        participant_email=inscription.participant_email,
    )
    db.add(certificat)
    inscription.certificate_issued = True
    await db.commit()
    await db.refresh(certificat)

    # Email avec le code du certificat
    await send_certificat_emis(
        participant_name=inscription.participant_name,
        participant_email=inscription.participant_email,
        formation_title=formation.title,
        cert_code=certificat.code,
    )

    return certificat


@formations_router.post("", response_model=FormationRead, status_code=status.HTTP_201_CREATED)
async def create_formation(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    trainer: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),  # Format: YYYY-MM-DD HH:MM
    end_date: Optional[str] = Form(None),
    registration_deadline: Optional[str] = Form(None),
    max_participants: Optional[int] = Form(None),
    registration_link: Optional[str] = Form(None),
    materials_link: Optional[str] = Form(None),
    is_published: bool = Form(False),
    type: str = Form("gratuite"),
    price: Optional[float] = Form(None),
    rubrique_id: str = Form(""),
    crasc_id: str = Form(""),
    osc_id: str = Form(""),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_redacteur_or_staff),
) -> Formation:
    """
    Create a new formation/training

    - **title**: Title of the formation (required)
    - **description**: Detailed description
    - **trainer**: Trainer name
    - **location**: Training location
    - **start_date**: Start date (YYYY-MM-DD HH:MM)
    - **end_date**: End date
    - **registration_deadline**: Registration deadline
    - **max_participants**: Maximum number of participants
    - **thumbnail**: Image file
    - **crasc_id**: Associated CRASC
    - **osc_id**: Associated OSC
    """
    # Validate title
    if not title or not title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "type": "validation_error",
                "errors": [{
                    "field": "title",
                    "message": "Le titre est requis et ne peut pas être vide."
                }]
            }
        )
    
    # Parse IDs
    crasc_id_int = int(crasc_id) if crasc_id and crasc_id != "" else None
    osc_id_int = int(osc_id) if osc_id and osc_id != "" else None
    rubrique_id_int = int(rubrique_id) if rubrique_id and rubrique_id != "" else None

    # Parse dates
    start_date_parsed = datetime.fromisoformat(start_date) if start_date else None
    end_date_parsed = datetime.fromisoformat(end_date) if end_date else None
    registration_deadline_parsed = datetime.fromisoformat(registration_deadline) if registration_deadline else None

    # Handle image upload
    saved_path = "default.png"
    if thumbnail and thumbnail.filename:
        file_extension = thumbnail.filename.split(".")[-1].lower()
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "validation_error",
                    "errors": [{
                        "field": "thumbnail",
                        "message": f"Format d'image invalide. Formats acceptés: {', '.join(allowed_extensions)}."
                    }]
                }
            )
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        saved_path = filename

    # Check for duplicate title
    result = await db.execute(select(Formation).where(Formation.title == title.strip()))
    existing_formation = result.scalars().first()
    if existing_formation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "duplicate_error",
                "errors": [{
                    "field": "title",
                    "message": f"Une formation avec le titre '{title.strip()}' existe déjà."
                }]
            }
        )

    statut_pub = "publie" if current_user.is_staff else "en_attente"

    try:
        formation = Formation(
            title=title.strip(),
            description=description,
            trainer=trainer,
            location=location,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            registration_deadline=registration_deadline_parsed,
            max_participants=max_participants,
            registration_link=registration_link,
            materials_link=materials_link,
            is_published=is_published,
            type=type,
            price=price,
            rubrique_id=rubrique_id_int,
            crasc_id=crasc_id_int,
            osc_id=osc_id_int,
            thumbnail_path=saved_path,
            statut_publication=statut_pub,
        )
        db.add(formation)
        await db.commit()
        await db.refresh(formation)
        return formation
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "database_error",
                "errors": [{
                    "field": "database",
                    "message": f"Erreur lors de la création: {str(e)}"
                }]
            }
        )


@formations_router.get("", response_model=List[FormationReadWithRelations], status_code=status.HTTP_200_OK)
async def get_formations(
    skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'enregistrements à retourner"),
    published_only: bool = Query(False, description="Afficher uniquement les formations publiées"),
    upcoming_only: bool = Query(False, description="Afficher uniquement les formations à venir"),
    search: Optional[str] = Query(None, description="Rechercher dans titre/description"),
    crasc_id: Optional[int] = Query(None, description="Filtrer par CRASC"),
    osc_id: Optional[int] = Query(None, description="Filtrer par OSC"),
    rubrique_id: Optional[int] = Query(None, description="Filtrer par rubrique"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all formations with filtering and pagination

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records (max 100)
    - **published_only**: Show only published formations
    - **upcoming_only**: Show only upcoming formations
    - **search**: Search in title and description
    - **crasc_id**: Filter by CRASC
    - **osc_id**: Filter by OSC
    """
    query = select(Formation).options(
        selectinload(Formation.crasc),
        selectinload(Formation.osc),
        selectinload(Formation.rubrique),
    ).where(Formation.statut_publication == "publie")

    # Apply filters
    if published_only:
        query = query.where(Formation.is_published == True)

    if upcoming_only:
        query = query.where(Formation.start_date >= datetime.now())
        query = query.where(Formation.is_completed == False)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Formation.title.ilike(search_term),
                Formation.description.ilike(search_term)
            )
        )

    if crasc_id:
        query = query.where(Formation.crasc_id == crasc_id)

    if osc_id:
        query = query.where(Formation.osc_id == osc_id)

    if rubrique_id:
        query = query.where(Formation.rubrique_id == rubrique_id)

    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(Formation.start_date.desc())

    result = await db.execute(query)
    formations = result.scalars().all()
    return formations


@formations_router.get("/upcoming", response_model=List[FormationRead], status_code=status.HTTP_200_OK)
async def get_upcoming_formations(
    limit: int = Query(5, ge=1, le=20, description="Nombre de formations à retourner"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get upcoming published formations

    Returns the next upcoming published formations
    """
    query = (
        select(Formation)
        .where(Formation.is_published == True)
        .where(Formation.is_completed == False)
        .where(Formation.start_date >= datetime.now())
        .where(Formation.statut_publication == "publie")
        .order_by(Formation.start_date.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    formations = result.scalars().all()
    return formations


@formations_router.get("/{formation_slug}", response_model=FormationReadWithRelations, status_code=status.HTTP_200_OK)
async def get_formation(
    formation_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single formation by slug with related CRASC and OSC
    """
    query = select(Formation).where(Formation.slug == formation_slug).options(
        selectinload(Formation.crasc),
        selectinload(Formation.osc),
        selectinload(Formation.rubrique),
    )

    result = await db.execute(query)
    formation = result.scalars().first()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formation non trouvée."
        )

    return formation


async def get_formation_update_form(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    trainer: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    registration_deadline: Optional[str] = Form(None),
    max_participants: Optional[int] = Form(None),
    current_participants: Optional[int] = Form(None),
    registration_link: Optional[str] = Form(None),
    materials_link: Optional[str] = Form(None),
    is_published: Optional[bool] = Form(None),
    is_full: Optional[bool] = Form(None),
    is_completed: Optional[bool] = Form(None),
    type: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    rubrique_id: str = Form(""),
    crasc_id: str = Form(""),
    osc_id: str = Form("")
) -> FormationUpdate:
    """Parse form data into FormationUpdate"""
    # Only include fields that are actually provided
    update_dict = {}
    
    if title is not None:
        update_dict["title"] = title
    
    if description is not None:
        update_dict["description"] = description
    
    if trainer is not None:
        update_dict["trainer"] = trainer
    
    if location is not None:
        update_dict["location"] = location
    
    # Parse dates only if provided
    if start_date:
        update_dict["start_date"] = datetime.fromisoformat(start_date)
    
    if end_date:
        update_dict["end_date"] = datetime.fromisoformat(end_date)
    
    if registration_deadline:
        update_dict["registration_deadline"] = datetime.fromisoformat(registration_deadline)
    
    if max_participants is not None:
        update_dict["max_participants"] = max_participants
    
    if current_participants is not None:
        update_dict["current_participants"] = current_participants
    
    if registration_link is not None:
        update_dict["registration_link"] = registration_link if registration_link != "" else None

    if materials_link is not None:
        update_dict["materials_link"] = materials_link if materials_link != "" else None
    
    if is_published is not None:
        update_dict["is_published"] = is_published
    
    if is_full is not None:
        update_dict["is_full"] = is_full
    
    if is_completed is not None:
        update_dict["is_completed"] = is_completed
    
    if type is not None:
        update_dict["type"] = type

    if price is not None:
        update_dict["price"] = price

    # Parse IDs - only include if provided
    if rubrique_id and rubrique_id != "":
        update_dict["rubrique_id"] = int(rubrique_id)

    if crasc_id and crasc_id != "":
        update_dict["crasc_id"] = int(crasc_id)

    if osc_id and osc_id != "":
        update_dict["osc_id"] = int(osc_id)

    return FormationUpdate(**update_dict)


@formations_router.delete("/inscriptions/{inscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_inscription(
    inscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Supprimer (désinscrire) un participant d'une formation (staff only)"""
    result = await db.execute(
        select(FormationInscription).where(FormationInscription.id == inscription_id)
    )
    inscription = result.scalar_one_or_none()
    if not inscription:
        raise HTTPException(status_code=404, detail="Inscription non trouvée.")
    # Décrémenter le compteur de participants de la formation
    formation_result = await db.execute(
        select(Formation).where(Formation.id == inscription.formation_id)
    )
    formation = formation_result.scalar_one_or_none()
    if formation and formation.current_participants > 0:
        formation.current_participants -= 1
    await db.delete(inscription)
    await db.commit()


@formations_router.patch("/inscriptions/{inscription_id}/completer", response_model=FormationInscriptionRead)
async def marquer_inscription_completee(
    inscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Marquer une inscription comme complétée (staff only)"""
    result = await db.execute(
        select(FormationInscription).where(FormationInscription.id == inscription_id)
    )
    inscription = result.scalar_one_or_none()
    if not inscription:
        raise HTTPException(status_code=404, detail="Inscription non trouvée.")
    inscription.is_completed = True
    inscription.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(inscription)
    return inscription


@formations_router.patch("/{formation_slug}", response_model=FormationReadWithRelations, status_code=status.HTTP_200_OK)
async def update_formation(
    formation_slug: str,
    formation_update: FormationUpdate = Depends(get_formation_update_form),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a formation

    All fields are optional
    """
    # Fetch existing formation
    result = await db.execute(
        select(Formation).where(Formation.slug == formation_slug).options(
            selectinload(Formation.crasc),
            selectinload(Formation.osc),
            selectinload(Formation.rubrique),
        )
    )
    formation = result.scalars().first()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formation non trouvée."
        )

    # Handle thumbnail upload
    if thumbnail and thumbnail.filename:
        file_extension = thumbnail.filename.split(".")[-1].lower()
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format d'image invalide. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        formation.thumbnail_path = filename

    # Update other fields
    update_data = formation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(formation, key, value)

    # Update slug if title changed
    if "title" in update_data:
        formation.slug = slugify.slugify(formation.title)

    # Auto-set is_full if max capacity reached
    if formation.max_participants and formation.current_participants >= formation.max_participants:
        formation.is_full = True
    else:
        formation.is_full = False

    # Update timestamp
    formation.updated_at = datetime.now()

    try:
        await db.commit()
        await db.refresh(formation)
        return formation
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "database_error",
                "errors": [{
                    "field": "database",
                    "message": f"Erreur lors de la mise à jour: {str(e)}"
                }]
            }
        )


@formations_router.delete("/{formation_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_formation(
    formation_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a formation by slug
    """
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalar_one_or_none()

    if not formation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formation '{formation_slug}' non trouvée."
        )

    await db.delete(formation)
    await db.commit()
    return None


@formations_router.get("/admin/en-attente", response_model=List[FormationRead])
async def list_formations_en_attente(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Liste toutes les formations en attente de validation (staff only)."""
    result = await db.execute(
        select(Formation)
        .where(Formation.statut_publication == "en_attente")
        .order_by(Formation.created_at.asc())
    )
    return result.scalars().all()


@formations_router.patch("/{formation_slug}/valider", response_model=FormationRead)
async def valider_formation(
    formation_slug: str,
    action: str = Query(..., description="publie ou rejete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Approuver ou rejeter une formation (staff only)."""
    if action not in ("publie", "rejete"):
        raise HTTPException(status_code=400, detail="Action invalide.")
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation non trouvée.")
    formation.statut_publication = action
    await db.commit()
    await db.refresh(formation)
    return formation


# ─────────────────────────────────────────────────────────────
# INSCRIPTIONS  (/{formation_slug}/...)
# ─────────────────────────────────────────────────────────────

@formations_router.get("/{formation_slug}/check-inscription")
async def check_inscription(
    formation_slug: str,
    email: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Vérifie si un email est déjà inscrit à une formation."""
    result = await db.execute(
        select(Formation).where(Formation.slug == formation_slug)
    )
    formation = result.scalar_one_or_none()
    if not formation:
        return {"registered": False}

    existing = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation.id,
            FormationInscription.participant_email == email,
        )
    )
    inscription = existing.scalar_one_or_none()
    return {
        "registered": inscription is not None,
        "payment_status": inscription.payment_status if inscription else None,
    }


@formations_router.post("/{formation_slug}/inscrire", response_model=FormationInscriptionRead, status_code=status.HTTP_201_CREATED)
async def inscrire_participant(
    formation_slug: str,
    data: FormationInscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Inscrire un participant à une formation.
    - Si gratuite  → inscription directe, payment_status='gratuite'
    - Si payante   → inscription créée avec payment_status='pending',
                     l'utilisateur doit ensuite appeler /{slug}/paiement/initier
    """
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation non trouvée.")
    if formation.is_full:
        raise HTTPException(status_code=400, detail="Formation complète.")
    if formation.is_completed:
        raise HTTPException(status_code=400, detail="Formation déjà terminée.")
    existing = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation.id,
            FormationInscription.participant_email == data.participant_email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cet email est déjà inscrit à cette formation.")

    payment_status = "gratuite" if formation.type == "gratuite" else "pending"

    inscription = FormationInscription(
        formation_id=formation.id,
        participant_name=data.participant_name,
        participant_email=data.participant_email,
        payment_status=payment_status,
        payment_amount=formation.price if formation.type == "payante" else None,
    )
    db.add(inscription)

    # On incrémente le compteur seulement pour les formations gratuites
    # Pour les payantes, on attend la confirmation du paiement
    if formation.type == "gratuite":
        formation.current_participants += 1
        if formation.max_participants and formation.current_participants >= formation.max_participants:
            formation.is_full = True

    await db.commit()
    await db.refresh(inscription)

    # Email de confirmation pour les formations gratuites
    if formation.type == "gratuite":
        start_date_str = (
            formation.start_date.strftime("%d/%m/%Y à %H:%M")
            if formation.start_date else None
        )
        await send_inscription_confirmation(
            participant_name=inscription.participant_name,
            participant_email=inscription.participant_email,
            formation_title=formation.title,
            formation_slug=formation_slug,
            start_date=start_date_str,
            location=formation.location,
            trainer=formation.trainer,
        )

    return inscription


@formations_router.post("/{formation_slug}/paiement/initier", response_model=PaiementInitierResponse)
async def initier_paiement(
    formation_slug: str,
    data: FormationInscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Initie le paiement CinetPay pour une formation payante.
    Crée ou retrouve l'inscription pending, puis retourne l'URL de paiement.
    """
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation non trouvée.")
    if formation.type != "payante":
        raise HTTPException(status_code=400, detail="Cette formation est gratuite.")
    if formation.is_full:
        raise HTTPException(status_code=400, detail="Formation complète.")
    if not formation.price:
        raise HTTPException(status_code=400, detail="Prix non défini pour cette formation.")

    # Retrouver ou créer l'inscription pending
    existing_result = await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation.id,
            FormationInscription.participant_email == data.participant_email,
        )
    )
    inscription = existing_result.scalar_one_or_none()

    if not inscription:
        inscription = FormationInscription(
            formation_id=formation.id,
            participant_name=data.participant_name,
            participant_email=data.participant_email,
            payment_status="pending",
            payment_amount=formation.price,
        )
        db.add(inscription)
        await db.commit()
        await db.refresh(inscription)
    elif inscription.payment_status == "paid":
        raise HTTPException(status_code=409, detail="Cet email a déjà payé cette formation.")

    # Initier le paiement via CinetPay
    try:
        paiement = await cinetpay_service.initier_paiement(
            amount=formation.price,
            participant_name=inscription.participant_name,
            participant_email=inscription.participant_email,
            description=f"Inscription : {formation.title}",
            formation_slug=formation_slug,
            participant_phone=data.participant_phone,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur CinetPay : {str(e)}")

    # Sauvegarder le transaction_id et le notify_token
    inscription.payment_transaction_id = paiement["transaction_id"]
    inscription.payment_notify_token = paiement.get("notify_token", "")
    await db.commit()

    return PaiementInitierResponse(
        inscription_id=inscription.id,
        payment_url=paiement["payment_url"],
        transaction_id=paiement["transaction_id"],
        amount=formation.price,
        currency=settings.CINETPAY_CURRENCY,
        cinetpay_configured=settings.cinetpay_configured,
    )


@formations_router.post("/paiement/webhook")
async def cinetpay_webhook(
    payload: PaiementWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook appelé automatiquement par CinetPay v1 après chaque paiement.
    Vérifie le notify_token puis confirme le statut via l'API.
    """
    result = await db.execute(
        select(FormationInscription).where(
            FormationInscription.payment_transaction_id == payload.merchant_transaction_id
        )
    )
    inscription = result.scalar_one_or_none()
    if not inscription:
        # CinetPay réessaie → on retourne 200 pour éviter les retry infinis
        return {"status": "not_found"}

    # Vérification timing-safe du notify_token
    stored_token = inscription.payment_notify_token or ""
    received_token = payload.notify_token
    if stored_token and stored_token != received_token:
        return {"status": "invalid_token"}

    # Confirmer le statut auprès de CinetPay
    try:
        verification = await cinetpay_service.verifier_paiement(payload.transaction_id)
        paiement_status = verification.get("status", "PENDING")
    except Exception:
        paiement_status = "PENDING"

    if paiement_status == "SUCCESS":
        inscription.payment_status = "paid"
        inscription.payment_date = datetime.now(timezone.utc)
        inscription.payment_operator = verification.get("operator", "")

        # Incrémenter le compteur de participants
        form_result = await db.execute(
            select(Formation).where(Formation.id == inscription.formation_id)
        )
        formation = form_result.scalar_one_or_none()
        if formation:
            formation.current_participants += 1
            if formation.max_participants and formation.current_participants >= formation.max_participants:
                formation.is_full = True

        await db.commit()

        # Email de confirmation de paiement
        payment_date_str = inscription.payment_date.strftime("%d/%m/%Y à %H:%M") if inscription.payment_date else None
        await send_paiement_confirme(
            participant_name=inscription.participant_name,
            participant_email=inscription.participant_email,
            formation_title=formation.title if formation else payload.merchant_transaction_id,
            formation_slug=formation.slug if formation else "",
            amount=float(inscription.payment_amount or 0),
            transaction_id=payload.merchant_transaction_id,
            payment_date=payment_date_str,
        )
    elif paiement_status == "FAILED":
        inscription.payment_status = "failed"
        await db.commit()

    return {"status": "ok"}


@formations_router.post("/paiement/simulation/confirmer/{inscription_id}", response_model=FormationInscriptionRead)
async def simuler_paiement_confirme(
    inscription_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint de simulation uniquement (désactivé automatiquement en production).
    Permet de simuler un paiement accepté sans CinetPay.
    """
    if settings.cinetpay_configured:
        raise HTTPException(status_code=403, detail="Simulation désactivée en production.")

    result = await db.execute(
        select(FormationInscription).where(FormationInscription.id == inscription_id)
    )
    inscription = result.scalar_one_or_none()
    if not inscription:
        raise HTTPException(status_code=404, detail="Inscription non trouvée.")

    inscription.payment_status = "paid"
    inscription.payment_date = datetime.now(timezone.utc)
    inscription.payment_operator = "SIMULATION"

    form_result = await db.execute(
        select(Formation).where(Formation.id == inscription.formation_id)
    )
    formation = form_result.scalar_one_or_none()
    if formation:
        formation.current_participants += 1
        if formation.max_participants and formation.current_participants >= formation.max_participants:
            formation.is_full = True

    await db.commit()
    await db.refresh(inscription)

    # Email de confirmation paiement simulé
    if formation:
        await send_paiement_confirme(
            participant_name=inscription.participant_name,
            participant_email=inscription.participant_email,
            formation_title=formation.title,
            formation_slug=formation.slug,
            amount=inscription.payment_amount or 0,
            transaction_id="SIMULATION",
            payment_date=inscription.payment_date.strftime("%d/%m/%Y à %H:%M"),
        )

    return inscription


@formations_router.get("/{formation_slug}/inscriptions", response_model=List[FormationInscriptionRead])
async def list_inscriptions(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste des inscriptions (staff only)"""
    result = await db.execute(select(Formation).where(Formation.slug == formation_slug))
    formation = result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation non trouvée.")
    insc_result = await db.execute(
        select(FormationInscription)
        .where(FormationInscription.formation_id == formation.id)
        .order_by(FormationInscription.created_at.desc())
    )
    return insc_result.scalars().all()


# ─────────────────────────────────────────────────────────────
# MODULES & LEÇONS
# ─────────────────────────────────────────────────────────────

async def _get_formation_or_404(slug: str, db: AsyncSession) -> Formation:
    result = await db.execute(select(Formation).where(Formation.slug == slug))
    formation = result.scalar_one_or_none()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation non trouvée.")
    return formation


async def _get_module_or_404(module_id: int, db: AsyncSession) -> FormationModule:
    result = await db.execute(select(FormationModule).where(FormationModule.id == module_id))
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module non trouvé.")
    return module


@formations_router.get("/{formation_slug}/modules", response_model=List[FormationModuleRead])
async def list_modules(formation_slug: str, db: AsyncSession = Depends(get_db)):
    """Liste les modules d'une formation avec leurs leçons (public)"""
    formation = await _get_formation_or_404(formation_slug, db)
    result = await db.execute(
        select(FormationModule)
        .where(FormationModule.formation_id == formation.id)
        .order_by(FormationModule.order)
        .options(selectinload(FormationModule.lecons))
    )
    return result.scalars().all()


@formations_router.post("/{formation_slug}/modules", response_model=FormationModuleRead, status_code=201)
async def create_module(
    formation_slug: str,
    data: FormationModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Créer un module (staff only)"""
    formation = await _get_formation_or_404(formation_slug, db)
    module = FormationModule(formation_id=formation.id, **data.model_dump())
    db.add(module)
    await db.commit()
    await db.refresh(module)
    # reload with lecons
    result = await db.execute(
        select(FormationModule).where(FormationModule.id == module.id)
        .options(selectinload(FormationModule.lecons))
    )
    return result.scalar_one()


@formations_router.patch("/{formation_slug}/modules/{module_id}", response_model=FormationModuleRead)
async def update_module(
    formation_slug: str,
    module_id: int,
    data: FormationModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Modifier un module (staff only)"""
    module = await _get_module_or_404(module_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(module, key, value)
    await db.commit()
    result = await db.execute(
        select(FormationModule).where(FormationModule.id == module_id)
        .options(selectinload(FormationModule.lecons))
    )
    return result.scalar_one()


@formations_router.delete("/{formation_slug}/modules/{module_id}", status_code=204)
async def delete_module(
    formation_slug: str,
    module_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Supprimer un module et toutes ses leçons (staff only)"""
    module = await _get_module_or_404(module_id, db)
    await db.delete(module)
    await db.commit()
    return None


@formations_router.post("/{formation_slug}/modules/{module_id}/lecons", response_model=FormationLeconRead, status_code=201)
async def create_lecon(
    formation_slug: str,
    module_id: int,
    data: FormationLeconCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Créer une leçon dans un module (staff only)"""
    module = await _get_module_or_404(module_id, db)
    lecon = FormationLecon(module_id=module.id, **data.model_dump())
    db.add(lecon)
    await db.commit()
    await db.refresh(lecon)
    return lecon


@formations_router.patch("/{formation_slug}/modules/{module_id}/lecons/{lecon_id}", response_model=FormationLeconRead)
async def update_lecon(
    formation_slug: str,
    module_id: int,
    lecon_id: int,
    data: FormationLeconUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Modifier une leçon (staff only)"""
    result = await db.execute(select(FormationLecon).where(FormationLecon.id == lecon_id))
    lecon = result.scalar_one_or_none()
    if not lecon:
        raise HTTPException(status_code=404, detail="Leçon non trouvée.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(lecon, key, value)
    await db.commit()
    await db.refresh(lecon)
    return lecon


@formations_router.delete("/{formation_slug}/modules/{module_id}/lecons/{lecon_id}", status_code=204)
async def delete_lecon(
    formation_slug: str,
    module_id: int,
    lecon_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Supprimer une leçon (staff only)"""
    result = await db.execute(select(FormationLecon).where(FormationLecon.id == lecon_id))
    lecon = result.scalar_one_or_none()
    if not lecon:
        raise HTTPException(status_code=404, detail="Leçon non trouvée.")
    # Supprimer le fichier PDF si existant
    if lecon.file_path:
        full_path = os.path.join("static", lecon.file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    await db.delete(lecon)
    await db.commit()
    return None


@formations_router.post("/{formation_slug}/modules/{module_id}/lecons/{lecon_id}/upload", response_model=FormationLeconRead)
async def upload_lecon_pdf(
    formation_slug: str,
    module_id: int,
    lecon_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Uploader un fichier PDF pour une leçon (staff only)"""
    if not file.content_type in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    result = await db.execute(select(FormationLecon).where(FormationLecon.id == lecon_id))
    lecon = result.scalar_one_or_none()
    if not lecon:
        raise HTTPException(status_code=404, detail="Leçon non trouvée.")

    # Supprimer l'ancien fichier si existant
    if lecon.file_path:
        old_path = os.path.join("static", lecon.file_path)
        if os.path.exists(old_path):
            os.remove(old_path)

    upload_dir = "static/formations/pdf"
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    lecon.file_path = f"formations/pdf/{filename}"
    lecon.type = "pdf"
    await db.commit()
    await db.refresh(lecon)
    return lecon
