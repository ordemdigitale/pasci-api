import os, shutil, uuid, slugify, secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, UploadFile, Depends, File, Form, Request, Query
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import desc, select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List, Annotated, Literal

from app.core.config import settings
from app.core.auth import (
    get_current_user,
    get_current_superuser,
    get_current_staff_or_superuser,
    get_optional_current_user,
    get_current_osc_user,
    check_crasc_ownership,
    check_osc_ownership,
)
from app.database.session import get_db
from app.models.users import User
from app.schemas.users import UserRead, CrascAdminCreate, OscUserCreate
from app.schemas.crasc import (
   CrascRead,
   CrascReadDetail,
   CrascUpdate,
   CrascContactCreate,
   RegionRead,
   RegionReadDetail,
   RegionUpdate,
   OscTypeRead,
   OscTypeReadDetail,
   OscTypeUpdate,
   OscRead,
   OscReadDetail,
   OscUpdate,
   NewsCreate,
   NewsRead,
   NewsReadDetail,
   NewsUpdate,
   EvenementCreate,
   EvenementRead,
   EvenementUpdate,
   CrascVideoCreate,
   CrascVideoRead,
   PaginatedResponse
)
from app.models.crasc import (
   Crasc, Region, OscType, Osc, News, Evenement, CrascVideo
)
from app.models.forum import PoleConcertation
from app.services.email import send_crasc_contact, send_welcome_osc
from app.services.file_uploads import save_formalisation_file, save_supporting_document


crasc_router = APIRouter()


def _adhesion_crasc_to_bool(statut: Optional[str], fallback: Optional[bool] = None) -> Optional[bool]:
    if statut == "oui":
        return True
    if statut == "non":
        return False
    return fallback


# ─────────────────────────── CRASC ───────────────────────────

@crasc_router.post("/crasc", response_model=CrascRead, status_code=status.HTTP_201_CREATED)
async def create_crasc(
   name: str = Form(...),
   description: Optional[str] = Form(None),
   osc_count: str = Form(""),
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_superuser),
):
   osc_count_int = int(osc_count) if osc_count and osc_count != "" else None
   crasc_create = Crasc(name=name, description=description, osc_count=osc_count_int)
   result = await db.execute(select(Crasc).where(Crasc.name == crasc_create.name))
   if result.scalars().first():
      raise HTTPException(
         status_code=status.HTTP_409_CONFLICT,
         detail={
            "type": "duplicate_error",
            "errors": [{"field": "name", "message": f"{name} existe déjà."}]
         }
      )
   try:
      db_crasc = Crasc(**crasc_create.model_dump())
      db.add(db_crasc)
      await db.commit()
      await db.refresh(db_crasc)
      return db_crasc
   except Exception as e:
      await db.rollback()
      raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.get("/crasc", response_model=List[CrascRead], status_code=status.HTTP_200_OK)
async def get_crascs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Liste les CRASCs. Un admin CRASC ne voit que le sien."""
    query = select(Crasc).offset(skip).limit(limit).order_by(Crasc.name)
    if current_user and current_user.is_staff and not current_user.is_superuser:
        query = query.where(Crasc.id == current_user.crasc_id)
    result = await db.execute(query)
    return result.scalars().all()


@crasc_router.get("/crasc/{crasc_slug}", response_model=CrascReadDetail, status_code=status.HTTP_200_OK)
async def get_crasc(
    crasc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    result = await db.execute(
        select(Crasc)
        .options(
            selectinload(Crasc.oscs),
            selectinload(Crasc.regions),
            selectinload(Crasc.news_items),
            selectinload(Crasc.evenements),
            selectinload(Crasc.videos),
        )
        .where(Crasc.slug == crasc_slug)
    )
    crasc = result.scalars().first()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")
    if current_user and current_user.is_staff and not current_user.is_superuser:
        check_crasc_ownership(current_user, crasc.id)
    return crasc


@crasc_router.patch("/crasc/{crasc_slug}", response_model=CrascReadDetail, status_code=status.HTTP_200_OK)
async def update_crasc(
    crasc_slug: str,
    crasc_update: CrascUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    result = await db.execute(
        select(Crasc)
        .where(Crasc.slug == crasc_slug)
        .options(selectinload(Crasc.oscs), selectinload(Crasc.regions), selectinload(Crasc.news_items))
    )
    crasc = result.scalars().first()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")
    update_data = crasc_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(crasc, key, value)
    if "name" in update_data:
        crasc.slug = slugify.slugify(crasc.name)
    await db.commit()
    await db.refresh(crasc)
    return crasc


@crasc_router.delete("/crasc/{crasc_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crasc(
    crasc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
    crasc = result.scalar_one_or_none()
    if not crasc:
        raise HTTPException(status_code=404, detail=f"{crasc_slug} non trouvé.")
    await db.delete(crasc)
    await db.commit()
    return None


# ─────────────────────────── RÉGION ───────────────────────────

@crasc_router.post("/region", response_model=RegionRead, status_code=status.HTTP_201_CREATED)
async def create_region(
    name: str = Form(...),
    crasc_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    # Un staff utilise obligatoirement son propre CRASC
    if current_user.is_staff and not current_user.is_superuser:
        resolved_crasc_id = current_user.crasc_id
    else:
        resolved_crasc_id = int(crasc_id) if crasc_id and crasc_id != "" else None

    region_create = Region(name=name, crasc_id=resolved_crasc_id)
    result = await db.execute(select(Region).where(Region.name == region_create.name))
    if result.scalars().first():
        raise HTTPException(
            status_code=409,
            detail={"type": "duplicate_error", "errors": [{"field": "name", "message": f"La région {name} existe déjà."}]}
        )
    try:
        db_region = Region(**region_create.model_dump())
        db.add(db_region)
        await db.commit()
        await db.refresh(db_region)
        return db_region
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.get("/region", response_model=list[RegionReadDetail], status_code=status.HTTP_200_OK)
async def get_regions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    query = select(Region).options(joinedload(Region.crasc)).offset(skip).limit(limit).order_by(Region.name)
    if current_user and current_user.is_staff and not current_user.is_superuser:
        query = query.where(Region.crasc_id == current_user.crasc_id)
    result = await db.execute(query)
    return result.scalars().all()


@crasc_router.get("/region/{region_slug}", response_model=RegionReadDetail, status_code=status.HTTP_200_OK)
async def get_region(region_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).where(Region.slug == region_slug).options(selectinload(Region.crasc)))
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Région non trouvée.")
    return region


@crasc_router.patch("/region/{region_slug}", response_model=RegionReadDetail, status_code=status.HTTP_200_OK)
async def update_region_civ_by_slug(
    region_slug: str,
    region_update: RegionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    result = await db.execute(select(Region).where(Region.slug == region_slug).options(selectinload(Region.crasc)))
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="Région non trouvée.")
    check_crasc_ownership(current_user, region.crasc_id)
    update_data = region_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(region, key, value)
    if "name" in update_data:
        region.slug = slugify.slugify(region.name)
    await db.commit()
    await db.refresh(region)
    return region


@crasc_router.delete("/region/{region_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_region(
    region_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    result = await db.execute(select(Region).where(Region.slug == region_slug))
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail=f"Region: {region_slug} non trouvé.")
    await db.delete(region)
    await db.commit()
    return None


# ─────────────────────────── OSC TYPE ───────────────────────────

@crasc_router.post("/osc-type", response_model=OscTypeRead, status_code=status.HTTP_201_CREATED)
async def create_osc_type(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> OscType:
    osctype_create = OscType(name=name, description=description)
    result = await db.execute(select(OscType).where(OscType.name == osctype_create.name))
    if result.scalars().first():
        raise HTTPException(
            status_code=409,
            detail={"type": "duplicate_error", "errors": [{"field": "name", "message": f"Le type {name} existe déjà."}]}
        )
    try:
        db_osctype = OscType(**osctype_create.model_dump())
        db.add(db_osctype)
        await db.commit()
        await db.refresh(db_osctype)
        return db_osctype
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.get("/osc-type", response_model=List[OscTypeRead], status_code=status.HTTP_200_OK)
async def get_all_osc_type(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    query = await db.execute(select(OscType).offset(skip).limit(limit).order_by(OscType.name))
    return query.scalars().all()


@crasc_router.get("/osc-type/{osctype_slug}", response_model=OscTypeReadDetail, status_code=status.HTTP_200_OK)
async def get_single_osc_type(osctype_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OscType).options(selectinload(OscType.oscs)).where(OscType.slug == osctype_slug))
    osc_type = result.scalars().first()
    if not osc_type:
        raise HTTPException(status_code=404, detail="Type de OSC non trouvé.")
    return osc_type


@crasc_router.patch("/osc-type/{osctype_slug}", response_model=OscTypeRead, status_code=status.HTTP_200_OK)
async def update_osc_type(
    osctype_slug: str,
    osctype_update: OscTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    result = await db.execute(select(OscType).where(OscType.slug == osctype_slug).options(selectinload(OscType.oscs)))
    osctype = result.scalars().first()
    if not osctype:
        raise HTTPException(status_code=404, detail="Type de OSC non trouvé.")
    update_data = osctype_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(osctype, key, value)
    if "name" in update_data:
        osctype.slug = slugify.slugify(osctype.name)
    await db.commit()
    await db.refresh(osctype)
    return osctype


@crasc_router.delete("/osc-type/{osctype_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_osc_type(
    osctype_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    result = await db.execute(select(OscType).where(OscType.slug == osctype_slug))
    osctype = result.scalar_one_or_none()
    if not osctype:
        raise HTTPException(status_code=404, detail=f"Type de OSC {osctype_slug} non trouvé.")
    await db.delete(osctype)
    await db.commit()
    return None


# ─────────────────────────── OSC ───────────────────────────

@crasc_router.post("/osc", response_model=OscRead, status_code=status.HTTP_201_CREATED)
async def create_osc(
    name: str = Form(...),
    sigle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
    type_id: str = Form(""),
    crasc_id: str = Form(""),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    region_nom: Optional[str] = Form(None),
    departement: Optional[str] = Form(None),
    sous_prefecture: Optional[str] = Form(None),
    ville: Optional[str] = Form(None),
    origine_organisation: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    type_document_formalisation: Optional[str] = Form(None),
    document_formalisation_file: Optional[UploadFile] = File(None),
    plan_action_document_file: Optional[UploadFile] = File(None),
    rapports_annuels_document_file: Optional[UploadFile] = File(None),
    adhesion_crasc_document_file: Optional[UploadFile] = File(None),
    existence_siege: Optional[bool] = Form(None),
    manuel_procedures: Optional[bool] = Form(None),
    plan_action: Optional[bool] = Form(None),
    rapports_annuels: Optional[bool] = Form(None),
    adhesion_crasc: Optional[bool] = Form(None),
    adhesion_crasc_statut: Optional[Literal["oui", "non", "en_cours"]] = Form(None),
    niveau_regroupement: Optional[Literal["Simple", "Réseau", "Fédération", "Plateforme", "Confédération"]] = Form(None),
    categorie: Optional[str] = Form(None),
    domaine_prioritaire: Optional[str] = Form(None),
    domaine_prioritaire_2: Optional[str] = Form(None),
    domaine_prioritaire_3: Optional[str] = Form(None),
    domaine_prioritaire_4: Optional[str] = Form(None),
    domaine_prioritaire_5: Optional[str] = Form(None),
    nb_membres: Optional[int] = Form(None),
    nb_femmes_membres: Optional[int] = Form(None),
    nb_hommes_membres: Optional[int] = Form(None),
    nb_membres_jeunes: Optional[int] = Form(None),
    nb_membres_handicap: Optional[int] = Form(None),
    nb_membres_be: Optional[int] = Form(None),
    nombre_mandats_be: Optional[int] = Form(None),
    duree_mandat_be: Optional[str] = Form(None),
    nb_beneficiaires: Optional[int] = Form(None),
    nb_femmes_beneficiaires: Optional[int] = Form(None),
    nb_jeunes_beneficiaires: Optional[int] = Form(None),
    nb_beneficiaires_handicap: Optional[int] = Form(None),
    organes_gouvernance: Optional[str] = Form(None),
    pays_couverture: Optional[str] = Form(None),
    nb_personnes_engagees: Optional[int] = Form(None),
    nb_cdi: Optional[int] = Form(None),
    nb_cdd: Optional[int] = Form(None),
    date_designation_responsable: Optional[str] = Form(None),
    date_prochaine_designation: Optional[str] = Form(None),
    plan_action_annee_cours: Optional[bool] = Form(None),
    plan_action_annee_cours_details: Optional[str] = Form(None),
    nb_activites: Optional[int] = Form(None),
    date_derniere_activite: Optional[str] = Form(None),
    recommandations: Optional[str] = Form(None),
    recommandations_2: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    type_id_int = int(type_id) if type_id and type_id != "" else None
    # Staff utilise toujours son propre CRASC
    if current_user.is_staff and not current_user.is_superuser:
        resolved_crasc_id = current_user.crasc_id
    else:
        resolved_crasc_id = int(crasc_id) if crasc_id and crasc_id != "" else None

    if thumbnail and thumbnail.filename:
        file_extension = thumbnail.filename.split(".")[-1]
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_extension.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail={"type": "validation_error", "errors": [{"field": "thumbnail", "message": f"Format invalide. Formats valides: {allowed_extensions}."}]}
            )
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        saved_path = filename
    else:
        saved_path = "default.png"
    saved_document_formalisation_path = save_formalisation_file(document_formalisation_file)
    saved_plan_action_document_path = save_supporting_document(
        plan_action_document_file,
        "plan_action_document_file",
        "osc-justificatifs/plan-action",
    )
    saved_rapports_annuels_document_path = save_supporting_document(
        rapports_annuels_document_file,
        "rapports_annuels_document_file",
        "osc-justificatifs/rapports-annuels",
    )
    saved_adhesion_crasc_document_path = save_supporting_document(
        adhesion_crasc_document_file,
        "adhesion_crasc_document_file",
        "osc-justificatifs/adhesion-crasc",
    )

    resolved_adhesion_crasc = _adhesion_crasc_to_bool(adhesion_crasc_statut, adhesion_crasc)

    db_osc = Osc(
        name=name, sigle=sigle, description=description, thumbnail_path=saved_path,
        type_id=type_id_int, crasc_id=resolved_crasc_id,
        email=email, phone=phone, region_nom=region_nom, departement=departement,
        sous_prefecture=sous_prefecture, ville=ville, origine_organisation=origine_organisation, address=address,
        latitude=latitude, longitude=longitude,
        type_document_formalisation=type_document_formalisation,
        document_formalisation_path=saved_document_formalisation_path,
        existence_siege=existence_siege,
        manuel_procedures=manuel_procedures,
        plan_action=plan_action,
        plan_action_document_path=saved_plan_action_document_path,
        rapports_annuels=rapports_annuels,
        rapports_annuels_document_path=saved_rapports_annuels_document_path,
        adhesion_crasc=resolved_adhesion_crasc,
        adhesion_crasc_statut=adhesion_crasc_statut,
        adhesion_crasc_document_path=saved_adhesion_crasc_document_path,
        niveau_regroupement=niveau_regroupement,
        categorie=categorie,
        domaine_prioritaire=domaine_prioritaire,
        domaine_prioritaire_2=domaine_prioritaire_2,
        domaine_prioritaire_3=domaine_prioritaire_3,
        domaine_prioritaire_4=domaine_prioritaire_4,
        domaine_prioritaire_5=domaine_prioritaire_5,
        nb_membres=nb_membres,
        nb_femmes_membres=nb_femmes_membres,
        nb_hommes_membres=nb_hommes_membres,
        nb_membres_jeunes=nb_membres_jeunes,
        nb_membres_handicap=nb_membres_handicap,
        nb_membres_be=nb_membres_be,
        nombre_mandats_be=nombre_mandats_be,
        duree_mandat_be=duree_mandat_be,
        nb_beneficiaires=nb_beneficiaires,
        nb_femmes_beneficiaires=nb_femmes_beneficiaires,
        nb_jeunes_beneficiaires=nb_jeunes_beneficiaires,
        nb_beneficiaires_handicap=nb_beneficiaires_handicap,
        organes_gouvernance=organes_gouvernance,
        pays_couverture=pays_couverture,
        nb_personnes_engagees=nb_personnes_engagees,
        nb_cdi=nb_cdi,
        nb_cdd=nb_cdd,
        date_designation_responsable=date_designation_responsable,
        date_prochaine_designation=date_prochaine_designation,
        plan_action_annee_cours=plan_action_annee_cours,
        plan_action_annee_cours_details=plan_action_annee_cours_details,
        nb_activites=nb_activites,
        date_derniere_activite=date_derniere_activite,
        recommandations=recommandations,
        recommandations_2=recommandations_2,
    )
    result = await db.execute(select(Osc).where(Osc.name == db_osc.name))
    if result.scalars().first():
        raise HTTPException(
            status_code=409,
            detail={"type": "duplicate_error", "errors": [{"field": "name", "message": "Une OSC avec ce nom existe déjà."}]}
        )
    try:
        osc_create = Osc(**db_osc.model_dump())
        db.add(osc_create)
        await db.commit()
        await db.refresh(osc_create)
        return osc_create
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.get("/osc", response_model=PaginatedResponse[OscReadDetail], status_code=status.HTTP_200_OK)
async def get_all_osc(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    type_id: Optional[int] = Query(None),
    crasc_id: Optional[int] = Query(None),
    region_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    type_document_formalisation: Optional[str] = Query(None),
    has_document_formalisation: Optional[bool] = Query(None),
    sort_by: Literal["name", "type_document_formalisation", "document_formalisation"] = Query("name"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    filters = []
    if type_id:
        filters.append(Osc.type_id == type_id)
    if region_id:
        filters.append(Osc.region_id == region_id)
    if search:
        term = f"%{search}%"
        filters.append((Osc.name.ilike(term)) | (Osc.description.ilike(term)))
    if type_document_formalisation:
        filters.append(Osc.type_document_formalisation == type_document_formalisation)
    if has_document_formalisation is True:
        filters.append(Osc.document_formalisation_path.is_not(None))
    elif has_document_formalisation is False:
        filters.append(Osc.document_formalisation_path.is_(None))

    # Un admin CRASC ne voit que les OSCs de son CRASC
    if current_user and current_user.is_staff and not current_user.is_superuser:
        filters.append(Osc.crasc_id == current_user.crasc_id)
    elif crasc_id:
        filters.append(Osc.crasc_id == crasc_id)

    count_query = select(func.count()).select_from(Osc)
    if filters:
        count_query = count_query.where(*filters)
    total = (await db.execute(count_query)).scalar()

    offset = (page - 1) * size
    query = select(Osc).options(
        selectinload(Osc.type), selectinload(Osc.crasc), selectinload(Osc.news_items), selectinload(Osc.poles)
    )
    if filters:
        query = query.where(*filters)
    if sort_by == "type_document_formalisation":
        order_column = Osc.type_document_formalisation
        query = query.order_by(order_column.asc() if sort_order == "asc" else order_column.desc(), Osc.name.asc())
    elif sort_by == "document_formalisation":
        has_no_document = Osc.document_formalisation_path.is_(None)
        query = query.order_by(has_no_document.asc() if sort_order == "asc" else has_no_document.desc(), Osc.name.asc())
    else:
        query = query.order_by(Osc.name.asc() if sort_order == "asc" else Osc.name.desc())
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=-(-total // size))


@crasc_router.get("/osc/me", response_model=OscReadDetail, status_code=status.HTTP_200_OK)
async def get_my_osc(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_osc_user),
):
    """Retourne l'OSC du compte utilisateur connecté."""
    query = select(Osc).where(Osc.id == current_user.osc_id).options(
        selectinload(Osc.type), selectinload(Osc.crasc), selectinload(Osc.news_items), selectinload(Osc.poles)
    )
    result = await db.execute(query)
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC introuvable.")
    return osc


@crasc_router.get("/osc/{osc_slug}", response_model=OscReadDetail, status_code=status.HTTP_200_OK)
async def get_osc_by_slug(
    osc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    query = select(Osc).where(Osc.slug == osc_slug).options(
        selectinload(Osc.type), selectinload(Osc.crasc), selectinload(Osc.news_items), selectinload(Osc.poles)
    )
    result = await db.execute(query)
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC non trouvée")
    if current_user and current_user.is_staff and not current_user.is_superuser:
        check_crasc_ownership(current_user, osc.crasc_id)
    return osc


async def get_osc_update_form(
    name: Optional[str] = Form(None),
    sigle: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    type_id: str = Form(""),
    crasc_id: str = Form(""),
    address: Optional[str] = Form(""),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    region_nom: Optional[str] = Form(None),
    departement: Optional[str] = Form(None),
    sous_prefecture: Optional[str] = Form(None),
    ville: Optional[str] = Form(None),
    origine_organisation: Optional[str] = Form(None),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    reseaux_sociaux: Optional[str] = Form(None),
    date_creation: Optional[str] = Form(None),
    numero_recepisse: Optional[str] = Form(None),
    type_document_formalisation: Optional[str] = Form(None),
    existence_siege: Optional[str] = Form(None),
    manuel_procedures: Optional[str] = Form(None),
    plan_action: Optional[str] = Form(None),
    rapports_annuels: Optional[str] = Form(None),
    niveau_couverture: Optional[str] = Form(None),
    zone_couverture: Optional[str] = Form(None),
    categorie: Optional[str] = Form(None),
    domaine_prioritaire: Optional[str] = Form(None),
    domaine_prioritaire_2: Optional[str] = Form(None),
    domaine_prioritaire_3: Optional[str] = Form(None),
    domaine_prioritaire_4: Optional[str] = Form(None),
    domaine_prioritaire_5: Optional[str] = Form(None),
    nb_membres: Optional[str] = Form(None),
    nb_femmes_membres: Optional[str] = Form(None),
    nb_hommes_membres: Optional[str] = Form(None),
    nb_membres_jeunes: Optional[str] = Form(None),
    nb_membres_handicap: Optional[str] = Form(None),
    nb_membres_be: Optional[str] = Form(None),
    nombre_mandats_be: Optional[str] = Form(None),
    nb_personnes_engagees: Optional[str] = Form(None),
    nb_cdi: Optional[str] = Form(None),
    nb_cdd: Optional[str] = Form(None),
    nb_beneficiaires: Optional[str] = Form(None),
    nb_femmes_beneficiaires: Optional[str] = Form(None),
    nb_jeunes_beneficiaires: Optional[str] = Form(None),
    nb_beneficiaires_handicap: Optional[str] = Form(None),
    nb_activites: Optional[str] = Form(None),
    date_derniere_activite: Optional[str] = Form(None),
    budget_annuel: Optional[str] = Form(None),
    type_financement: Optional[str] = Form(None),
    etat_cotisations: Optional[str] = Form(None),
    montant_cotisation: Optional[str] = Form(None),
    nom_president: Optional[str] = Form(None),
    sexe_president: Optional[str] = Form(None),
    mode_designation_president: Optional[str] = Form(None),
    date_designation_responsable: Optional[str] = Form(None),
    date_prochaine_designation: Optional[str] = Form(None),
    duree_mandat_be: Optional[str] = Form(None),
    adhesion_crasc: Optional[str] = Form(None),
    adhesion_crasc_statut: Optional[str] = Form(None),
    niveau_regroupement: Optional[str] = Form(None),
    reseau_appartenance: Optional[str] = Form(None),
    organes_gouvernance: Optional[str] = Form(None),
    pays_couverture: Optional[str] = Form(None),
    plan_action_annee_cours: Optional[str] = Form(None),
    plan_action_annee_cours_details: Optional[str] = Form(None),
    secteurs_activites: Optional[str] = Form(None),
    populations_cibles: Optional[str] = Form(None),
    savoir_faire: Optional[str] = Form(None),
    difficultes: Optional[str] = Form(None),
    recommandations: Optional[str] = Form(None),
    recommandations_2: Optional[str] = Form(None),
) -> OscUpdate:
    def to_int(v): return int(v) if v and v.strip() != "" else None
    def to_float(v): return float(v) if v and v.strip() != "" else None
    def to_bool(v): return True if v == "true" else (False if v == "false" else None)
    resolved_adhesion_crasc = _adhesion_crasc_to_bool(adhesion_crasc_statut, to_bool(adhesion_crasc))

    return OscUpdate(
        name=name, sigle=sigle, description=description,
        type_id=to_int(type_id), crasc_id=to_int(crasc_id),
        address=address, email=email, phone=phone, region_nom=region_nom,
        departement=departement, sous_prefecture=sous_prefecture, ville=ville,
        origine_organisation=origine_organisation,
        latitude=to_float(latitude), longitude=to_float(longitude),
        website=website, reseaux_sociaux=reseaux_sociaux,
        date_creation=date_creation, numero_recepisse=numero_recepisse,
        type_document_formalisation=type_document_formalisation,
        existence_siege=to_bool(existence_siege),
        manuel_procedures=to_bool(manuel_procedures),
        plan_action=to_bool(plan_action),
        rapports_annuels=to_bool(rapports_annuels),
        niveau_couverture=niveau_couverture, zone_couverture=zone_couverture,
        categorie=categorie,
        domaine_prioritaire=domaine_prioritaire, domaine_prioritaire_2=domaine_prioritaire_2,
        domaine_prioritaire_3=domaine_prioritaire_3, domaine_prioritaire_4=domaine_prioritaire_4,
        domaine_prioritaire_5=domaine_prioritaire_5,
        nb_membres=to_int(nb_membres), nb_femmes_membres=to_int(nb_femmes_membres),
        nb_hommes_membres=to_int(nb_hommes_membres),
        nb_membres_jeunes=to_int(nb_membres_jeunes),
        nb_membres_handicap=to_int(nb_membres_handicap),
        nb_membres_be=to_int(nb_membres_be),
        nombre_mandats_be=to_int(nombre_mandats_be),
        nb_personnes_engagees=to_int(nb_personnes_engagees),
        nb_cdi=to_int(nb_cdi), nb_cdd=to_int(nb_cdd),
        nb_beneficiaires=to_int(nb_beneficiaires),
        nb_femmes_beneficiaires=to_int(nb_femmes_beneficiaires),
        nb_jeunes_beneficiaires=to_int(nb_jeunes_beneficiaires),
        nb_beneficiaires_handicap=to_int(nb_beneficiaires_handicap),
        nb_activites=to_int(nb_activites), date_derniere_activite=date_derniere_activite,
        budget_annuel=to_int(budget_annuel), type_financement=type_financement,
        etat_cotisations=etat_cotisations, montant_cotisation=to_int(montant_cotisation),
        nom_president=nom_president, sexe_president=sexe_president,
        mode_designation_president=mode_designation_president,
        date_designation_responsable=date_designation_responsable,
        date_prochaine_designation=date_prochaine_designation,
        duree_mandat_be=duree_mandat_be,
        adhesion_crasc=resolved_adhesion_crasc, adhesion_crasc_statut=adhesion_crasc_statut,
        niveau_regroupement=niveau_regroupement,
        reseau_appartenance=reseau_appartenance, organes_gouvernance=organes_gouvernance,
        pays_couverture=pays_couverture,
        plan_action_annee_cours=to_bool(plan_action_annee_cours),
        plan_action_annee_cours_details=plan_action_annee_cours_details,
        secteurs_activites=secteurs_activites, populations_cibles=populations_cibles,
        savoir_faire=savoir_faire, difficultes=difficultes, recommandations=recommandations,
        recommandations_2=recommandations_2,
    )


@crasc_router.patch("/osc/{osc_slug}", response_model=OscRead)
async def update_osc_with_form(
    osc_slug: str,
    osc_update: OscUpdate = Depends(get_osc_update_form),
    thumbnail: Optional[UploadFile] = File(None),
    document_formalisation_file: Optional[UploadFile] = File(None),
    plan_action_document_file: Optional[UploadFile] = File(None),
    rapports_annuels_document_file: Optional[UploadFile] = File(None),
    adhesion_crasc_document_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Osc).where(Osc.slug == osc_slug).options(selectinload(Osc.type), selectinload(Osc.crasc), selectinload(Osc.poles))
    )
    osc = result.scalars().first()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC non trouvée")

    # Vérification des droits
    if not (current_user.is_staff or current_user.is_superuser):
        # L'utilisateur doit être rattaché à cette OSC
        check_osc_ownership(current_user, osc.id)

    if current_user.is_staff and not current_user.is_superuser:
        check_crasc_ownership(current_user, osc.crasc_id)

    if thumbnail and thumbnail.filename:
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        file_extension = thumbnail.filename.split(".")[-1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Format invalide. Formats acceptés: {', '.join(allowed_extensions)}")
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        osc.thumbnail_path = filename

    saved_document_formalisation_path = save_formalisation_file(document_formalisation_file)
    if saved_document_formalisation_path:
        osc.document_formalisation_path = saved_document_formalisation_path
    saved_plan_action_document_path = save_supporting_document(
        plan_action_document_file,
        "plan_action_document_file",
        "osc-justificatifs/plan-action",
    )
    if saved_plan_action_document_path:
        osc.plan_action_document_path = saved_plan_action_document_path
    saved_rapports_annuels_document_path = save_supporting_document(
        rapports_annuels_document_file,
        "rapports_annuels_document_file",
        "osc-justificatifs/rapports-annuels",
    )
    if saved_rapports_annuels_document_path:
        osc.rapports_annuels_document_path = saved_rapports_annuels_document_path
    saved_adhesion_crasc_document_path = save_supporting_document(
        adhesion_crasc_document_file,
        "adhesion_crasc_document_file",
        "osc-justificatifs/adhesion-crasc",
    )
    if saved_adhesion_crasc_document_path:
        osc.adhesion_crasc_document_path = saved_adhesion_crasc_document_path

    update_data = {k: v for k, v in osc_update.model_dump().items() if v is not None}
    # Staff et utilisateurs OSC ne peuvent pas changer le crasc_id
    if not current_user.is_superuser:
        update_data.pop("crasc_id", None)
    for key, value in update_data.items():
        setattr(osc, key, value)
    if "name" in update_data:
        base_slug = slugify.slugify(osc.name)[:95]
        new_slug = base_slug
        n = 1
        while True:
            conflict = await db.execute(select(Osc).where(Osc.slug == new_slug, Osc.id != osc.id))
            if not conflict.scalars().first():
                break
            n += 1
            new_slug = f"{base_slug}-{n}"
        osc.slug = new_slug

    try:
        await db.commit()
        await db.refresh(osc)
        return osc
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.delete("/osc/{osc_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_osc(
    osc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    result = await db.execute(select(Osc).where(Osc.slug == osc_slug))
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail=f"Osc {osc_slug} non trouvée.")
    check_crasc_ownership(current_user, osc.crasc_id)
    await db.delete(osc)
    await db.commit()
    return None


@crasc_router.patch("/osc/{osc_slug}/poles", response_model=OscReadDetail)
async def update_osc_poles(
    osc_slug: str,
    pole_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remplace les pôles de concertation (domaines prioritaires) d'une OSC."""
    result = await db.execute(
        select(Osc).where(Osc.slug == osc_slug).options(
            selectinload(Osc.type), selectinload(Osc.crasc),
            selectinload(Osc.news_items), selectinload(Osc.poles)
        )
    )
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC non trouvée")

    if not (current_user.is_staff or current_user.is_superuser):
        check_osc_ownership(current_user, osc.id)
    if current_user.is_staff and not current_user.is_superuser:
        check_crasc_ownership(current_user, osc.crasc_id)

    # Charger les pôles demandés
    poles_result = await db.execute(
        select(PoleConcertation).where(PoleConcertation.id.in_(pole_ids))
    )
    new_poles = list(poles_result.scalars().all())
    osc.poles = new_poles

    await db.commit()
    await db.refresh(osc)
    return osc


# ─────────────────────────── NEWS ───────────────────────────

@crasc_router.post("/news", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
async def create_news(
    title: str = Form(...),
    content: Optional[str] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
    crasc_id: str = Form(""),
    osc_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    osc_id_int = int(osc_id) if osc_id and osc_id != "" else None
    # Staff utilise son propre CRASC
    if current_user.is_staff and not current_user.is_superuser:
        resolved_crasc_id = current_user.crasc_id
    else:
        resolved_crasc_id = int(crasc_id) if crasc_id and crasc_id != "" else None

    if thumbnail and thumbnail.filename:
        file_extension = thumbnail.filename.split(".")[-1]
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_extension.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail={"type": "validation_error", "errors": [{"field": "thumbnail", "message": f"Format invalide. Formats valides: {allowed_extensions}."}]}
            )
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(thumbnail.file, buffer)
        saved_path = filename
    else:
        saved_path = "default.png"

    news_create = News(title=title, content=content, crasc_id=resolved_crasc_id, osc_id=osc_id_int, thumbnail_path=saved_path)
    result = await db.execute(select(News).where(News.title == news_create.title))
    if result.scalars().first():
        raise HTTPException(
            status_code=409,
            detail={"type": "duplicate_error", "errors": [{"field": "title", "message": "Une actualité avec ce titre existe déjà."}]}
        )
    try:
        db_news = News(**news_create.model_dump())
        db.add(db_news)
        await db.commit()
        await db.refresh(db_news)
        return db_news
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.get("/news", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
async def get_all_news(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    crasc_id: Optional[int] = None,
    osc_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    statement = select(News).options(selectinload(News.crasc), selectinload(News.osc)).offset(skip).limit(limit).order_by(desc(News.id))

    # Un admin CRASC ne voit que les news de son CRASC
    if current_user and current_user.is_staff and not current_user.is_superuser:
        statement = statement.where(News.crasc_id == current_user.crasc_id)
    else:
        if crasc_id:
            statement = statement.where(News.crasc_id == crasc_id)

    if osc_id:
        statement = statement.where(News.osc_id == osc_id)

    result = await db.execute(statement)
    return result.scalars().all()


@crasc_router.get("/news/{news_slug}", response_model=NewsReadDetail, status_code=status.HTTP_200_OK)
async def get_single_news_item(news_slug: str, db: AsyncSession = Depends(get_db)):
    query = select(News).where(News.slug == news_slug).options(selectinload(News.crasc), selectinload(News.osc))
    result = await db.execute(query)
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Actualité non trouvée.")
    return news


@crasc_router.delete("/news/{news_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    result = await db.execute(select(News).where(News.slug == news_slug))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail=f"Article {news_slug} non trouvé.")
    check_crasc_ownership(current_user, news.crasc_id)
    await db.delete(news)
    await db.commit()
    return None


# ─────────────────────────── ADMIN CRASC ───────────────────────────

@crasc_router.get("/crasc/{crasc_slug}/admin", response_model=Optional[UserRead], status_code=status.HTTP_200_OK)
async def get_crasc_admin(
    crasc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Retourne l'admin (staff) rattaché à ce CRASC."""
    result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
    crasc = result.scalar_one_or_none()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")
    admin_result = await db.execute(
        select(User).where(User.crasc_id == crasc.id, User.is_staff == True)
    )
    return admin_result.scalar_one_or_none()


@crasc_router.post("/crasc/{crasc_slug}/admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_crasc_admin(
    crasc_slug: str,
    admin_data: CrascAdminCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Crée un compte admin pour ce CRASC (superuser uniquement)."""
    result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
    crasc = result.scalar_one_or_none()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")

    # Vérifier qu'il n'y a pas déjà un admin pour ce CRASC
    existing = await db.execute(
        select(User).where(User.crasc_id == crasc.id, User.is_staff == True)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce CRASC a déjà un administrateur. Supprimez-le avant d'en créer un nouveau."
        )

    # Vérifier l'unicité email / username
    if (await db.execute(select(User).where(User.email == admin_data.email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")
    if admin_data.username:
        if (await db.execute(select(User).where(User.username == admin_data.username))).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Ce nom d'utilisateur est déjà pris.")

    new_admin = User(
        email=admin_data.email,
        username=admin_data.username,
        first_name=admin_data.first_name,
        last_name=admin_data.last_name,
        is_staff=True,
        is_active=True,
        crasc_id=crasc.id,
    )
    new_admin.set_password(admin_data.password)
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin


@crasc_router.put("/crasc/{crasc_slug}/admin/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def assign_crasc_admin(
    crasc_slug: str,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Assigne un utilisateur existant comme admin de ce CRASC (superuser uniquement)."""
    result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
    crasc = result.scalar_one_or_none()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")

    # Vérifier qu'il n'y a pas déjà un admin différent pour ce CRASC
    existing = await db.execute(
        select(User).where(User.crasc_id == crasc.id, User.is_staff == True, User.id != user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce CRASC a déjà un administrateur. Révoquez-le avant d'en assigner un nouveau."
        )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")

    user.is_staff = True
    user.crasc_id = crasc.id
    await db.commit()
    await db.refresh(user)
    return user


@crasc_router.delete("/crasc/{crasc_slug}/admin", status_code=status.HTTP_204_NO_CONTENT)
async def remove_crasc_admin(
    crasc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Révoque l'admin de ce CRASC (désactive is_staff et détache du CRASC)."""
    result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
    crasc = result.scalar_one_or_none()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")
    admin_result = await db.execute(
        select(User).where(User.crasc_id == crasc.id, User.is_staff == True)
    )
    admin = admin_result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Aucun admin trouvé pour ce CRASC.")
    admin.is_staff = False
    admin.crasc_id = None
    await db.commit()
    return None


# ─────────────────────────── OSC USER MANAGEMENT ───────────────────────────

@crasc_router.get("/osc/{osc_slug}/user", response_model=Optional[UserRead], status_code=status.HTTP_200_OK)
async def get_osc_user(
    osc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    """Retourne le compte utilisateur rattaché à cette OSC."""
    result = await db.execute(select(Osc).where(Osc.slug == osc_slug))
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC non trouvée.")
    user_result = await db.execute(select(User).where(User.osc_id == osc.id))
    return user_result.scalar_one_or_none()


@crasc_router.post("/osc/{osc_slug}/user", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_osc_user(
    osc_slug: str,
    user_data: OscUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    """Crée un compte utilisateur pour une OSC (staff/superuser uniquement)."""
    result = await db.execute(select(Osc).where(Osc.slug == osc_slug))
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC non trouvée.")
    if current_user.is_staff and not current_user.is_superuser:
        check_crasc_ownership(current_user, osc.crasc_id)

    existing = await db.execute(select(User).where(User.osc_id == osc.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cette OSC a déjà un compte utilisateur.")

    if (await db.execute(select(User).where(User.email == user_data.email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")
    if user_data.username:
        if (await db.execute(select(User).where(User.username == user_data.username))).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Ce nom d'utilisateur est déjà pris.")

    token = secrets.token_urlsafe(32)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        osc_id=osc.id,
        reset_token=token,
        reset_token_expires=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    new_user.set_password(user_data.password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    try:
        await send_welcome_osc(
            user_name=new_user.full_name or new_user.get_username(),
            user_email=new_user.email,
            osc_name=osc.name,
            token=token,
        )
    except Exception:
        pass  # Ne pas bloquer la création si l'email échoue

    return new_user


@crasc_router.delete("/osc/{osc_slug}/user", status_code=status.HTTP_204_NO_CONTENT)
async def delete_osc_user(
    osc_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    """Supprime le compte utilisateur rattaché à cette OSC."""
    result = await db.execute(select(Osc).where(Osc.slug == osc_slug))
    osc = result.scalar_one_or_none()
    if not osc:
        raise HTTPException(status_code=404, detail="OSC non trouvée.")
    if current_user.is_staff and not current_user.is_superuser:
        check_crasc_ownership(current_user, osc.crasc_id)
    user_result = await db.execute(select(User).where(User.osc_id == osc.id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Aucun compte utilisateur trouvé pour cette OSC.")
    user.osc_id = None
    await db.commit()
    return None


# ─────────────────────────── AGENDA / ÉVÉNEMENTS ───────────────────────────

@crasc_router.post("/evenement", response_model=EvenementRead, status_code=status.HTTP_201_CREATED)
async def create_evenement(
    evenement_in: EvenementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    """Crée un événement dans l'agenda d'un CRASC."""
    if current_user.is_staff and not current_user.is_superuser:
        resolved_crasc_id = current_user.crasc_id
    else:
        resolved_crasc_id = evenement_in.crasc_id

    db_evt = Evenement(
        title=evenement_in.title,
        description=evenement_in.description,
        date_debut=evenement_in.date_debut,
        date_fin=evenement_in.date_fin,
        lieu=evenement_in.lieu,
        crasc_id=resolved_crasc_id,
    )
    db.add(db_evt)
    try:
        await db.commit()
        await db.refresh(db_evt)
        return db_evt
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail={"type": "database_error", "errors": [{"field": "database", "message": str(e)}]})


@crasc_router.get("/evenement", response_model=List[EvenementRead], status_code=status.HTTP_200_OK)
async def get_evenements(
    crasc_id: Optional[int] = None,
    a_venir: bool = Query(True, description="Si True, retourne uniquement les événements futurs"),
    db: AsyncSession = Depends(get_db),
):
    """Liste les événements. Filtre par CRASC et/ou par date (futurs uniquement par défaut)."""
    from datetime import datetime, timezone as tz
    stmt = select(Evenement).order_by(Evenement.date_debut)
    if crasc_id:
        stmt = stmt.where(Evenement.crasc_id == crasc_id)
    if a_venir:
        stmt = stmt.where(Evenement.date_debut >= datetime.now(tz.utc))
    result = await db.execute(stmt)
    return result.scalars().all()


@crasc_router.get("/evenement/{evenement_id}", response_model=EvenementRead, status_code=status.HTTP_200_OK)
async def get_evenement(evenement_id: int, db: AsyncSession = Depends(get_db)):
    evt = await db.get(Evenement, evenement_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Événement non trouvé.")
    return evt


@crasc_router.patch("/evenement/{evenement_id}", response_model=EvenementRead, status_code=status.HTTP_200_OK)
async def update_evenement(
    evenement_id: int,
    evt_update: EvenementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    evt = await db.get(Evenement, evenement_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Événement non trouvé.")
    check_crasc_ownership(current_user, evt.crasc_id)
    for key, value in evt_update.model_dump(exclude_unset=True).items():
        setattr(evt, key, value)
    await db.commit()
    await db.refresh(evt)
    return evt


@crasc_router.delete("/evenement/{evenement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evenement(
    evenement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    evt = await db.get(Evenement, evenement_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Événement non trouvé.")
    check_crasc_ownership(current_user, evt.crasc_id)
    await db.delete(evt)
    await db.commit()
    return None


# ─────────────────────────── CONTACT CRASC ───────────────────────────

@crasc_router.post("/crasc/{crasc_slug}/contact", status_code=status.HTTP_200_OK)
async def contact_crasc(
    crasc_slug: str,
    data: CrascContactCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Envoie un message de contact au PDOC et au PCA du CRASC. Public."""
    result = await db.execute(select(Crasc).where(Crasc.slug == crasc_slug))
    crasc = result.scalar_one_or_none()
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")

    background_tasks.add_task(
        send_crasc_contact,
        nom=data.nom,
        email=data.email,
        telephone=data.telephone,
        objet=data.objet,
        message=data.message,
        crasc_name=crasc.name,
        email_pca=crasc.email_pca,
    )
    return {"detail": "Message transmis avec succès."}


# ─────────────────────────── CRASC VIDEOS ───────────────────────────

@crasc_router.get("/video", response_model=List[CrascVideoRead], status_code=status.HTTP_200_OK)
async def list_crasc_videos(
    crasc_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lister les vidéos d'un CRASC (public)."""
    query = select(CrascVideo).order_by(CrascVideo.ordre, CrascVideo.created_at)
    if crasc_id:
        query = query.where(CrascVideo.crasc_id == crasc_id)
    result = await db.execute(query)
    return result.scalars().all()


@crasc_router.post("/video", response_model=CrascVideoRead, status_code=status.HTTP_201_CREATED)
async def create_crasc_video(
    data: CrascVideoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    """Ajouter une vidéo à un CRASC."""
    crasc = await db.get(Crasc, data.crasc_id)
    if not crasc:
        raise HTTPException(status_code=404, detail="CRASC non trouvé.")
    check_crasc_ownership(current_user, data.crasc_id)
    video = CrascVideo(**data.model_dump())
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


@crasc_router.delete("/video/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crasc_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_superuser),
):
    """Supprimer une vidéo d'un CRASC."""
    video = await db.get(CrascVideo, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vidéo non trouvée.")
    check_crasc_ownership(current_user, video.crasc_id)
    await db.delete(video)
    await db.commit()
    return None


@crasc_router.get("/news-spotlight-crasc", response_model=List[NewsReadDetail], status_code=status.HTTP_200_OK)
async def get_spotlight_news_per_crasc(db: AsyncSession = Depends(get_db)):
    query = (
        select(News)
        .distinct(News.crasc_id)
        .where(News.crasc_id.is_not(None))
        .options(joinedload(News.crasc), joinedload(News.osc))
        .order_by(News.crasc_id, News.id.desc())
    )
    result = await db.execute(query)
    return result.unique().scalars().all()
