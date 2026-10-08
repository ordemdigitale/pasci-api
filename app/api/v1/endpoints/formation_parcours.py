# app/api/v1/endpoints/formation_parcours.py
"""
Supports de formation (« lucarne » de la page formation) et évaluation finale
(QCM) préalable à la délivrance du certificat.

Accès et certification : app/services/formation_acces.py.
"""
import json
import os
import uuid
from typing import Dict, List, Optional

import slugify
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_staff_user, get_current_user, get_optional_current_user
from app.core.config import settings
from app.database.session import get_db
from app.models.formation import Formation, FormationQuestion, FormationSupport, FormationTentative
from app.models.users import User
from app.services import formation_acces
from app.services.email import send_certificat_emis

formation_parcours_router = APIRouter()

DOSSIER_SUPPORTS = "formations-supports"
EXTENSIONS_SUPPORTS = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "odt", "odp", "ods",
    "txt", "csv", "zip", "jpg", "jpeg", "png", "mp3", "mp4",
}


async def _formation(db: AsyncSession, slug: str) -> Formation:
    formation = (await db.execute(select(Formation).where(Formation.slug == slug))).scalars().first()
    if not formation:
        raise HTTPException(status_code=404, detail="Formation non trouvée.")
    return formation


# ─────────────────────────────────────────────────────
# SUPPORTS DE FORMATION
# ─────────────────────────────────────────────────────

class SupportRead(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    type: str
    nom: Optional[str] = None
    taille: int = 0
    public: bool
    ordre: int
    # Vide si le support est réservé et que l'utilisateur n'y a pas accès
    url: Optional[str] = None
    verrouille: bool = False


def _serialiser_support(support: FormationSupport, acces: bool) -> SupportRead:
    visible = acces or support.public
    url = None
    if visible:
        url = support.url if support.type == "lien" else f"{settings.API_BASE_URL}/static/{support.chemin}"
    return SupportRead(
        id=support.id, titre=support.titre, description=support.description, type=support.type,
        nom=support.nom_original, taille=support.taille, public=support.public, ordre=support.ordre,
        url=url, verrouille=not visible,
    )


@formation_parcours_router.get("/{formation_slug}/supports", response_model=List[SupportRead])
async def lister_supports(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Supports de la formation (public : les supports réservés sont listés mais verrouillés)."""
    formation = await _formation(db, formation_slug)
    acces = formation_acces.est_staff(current_user) or formation_acces.a_acces(
        await formation_acces.inscription_de(db, formation.id, current_user)
    )
    supports = (await db.execute(
        select(FormationSupport)
        .where(FormationSupport.formation_id == formation.id)
        .order_by(FormationSupport.ordre, FormationSupport.id)
    )).scalars().all()
    return [_serialiser_support(s, acces) for s in supports]


@formation_parcours_router.post("/{formation_slug}/supports", response_model=SupportRead, status_code=status.HTTP_201_CREATED)
async def ajouter_support(
    formation_slug: str,
    titre: str = Form(...),
    description: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    public: bool = Form(False),
    ordre: int = Form(0),
    fichier: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Ajoute un support : un fichier (PDF, Word, PowerPoint…) OU un lien (staff)."""
    formation = await _formation(db, formation_slug)
    titre = titre.strip()
    if not titre:
        raise HTTPException(status_code=422, detail="Le titre est requis.")
    a_fichier = bool(fichier and fichier.filename)
    url = (url or "").strip()
    if a_fichier == bool(url):
        raise HTTPException(status_code=422, detail="Joignez un fichier OU indiquez un lien.")

    support = FormationSupport(
        formation_id=formation.id, titre=titre[:200], description=(description or "").strip() or None,
        public=public, ordre=ordre,
    )
    if url:
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail="Le lien doit commencer par http:// ou https://.")
        support.type, support.url = "lien", url[:1000]
    else:
        base, extension = os.path.splitext(os.path.basename(fichier.filename))
        extension = extension.lstrip(".").lower()
        if extension not in EXTENSIONS_SUPPORTS:
            raise HTTPException(
                status_code=400,
                detail=f"Format non accepté. Formats acceptés : {', '.join(sorted(EXTENSIONS_SUPPORTS))}.",
            )
        max_octets = settings.FORMATION_SUPPORT_MAX_MO * 1024 * 1024
        dossier = os.path.join(settings.UPLOAD_DIR, DOSSIER_SUPPORTS)
        os.makedirs(dossier, exist_ok=True)
        nom_stocke = f"{uuid.uuid4().hex}_{slugify.slugify(base)[:80] or 'support'}.{extension}"
        chemin_disque = os.path.join(dossier, nom_stocke)
        taille = 0
        with open(chemin_disque, "wb") as sortie:
            while bloc := await fichier.read(1024 * 1024):
                taille += len(bloc)
                if taille > max_octets:
                    sortie.close()
                    os.remove(chemin_disque)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Le fichier dépasse {settings.FORMATION_SUPPORT_MAX_MO} Mo.",
                    )
                sortie.write(bloc)
        support.type, support.chemin = "fichier", f"{DOSSIER_SUPPORTS}/{nom_stocke}"
        support.nom_original, support.taille = fichier.filename[:255], taille
    db.add(support)
    await db.commit()
    await db.refresh(support)
    return _serialiser_support(support, True)


@formation_parcours_router.delete("/{formation_slug}/supports/{support_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_support(
    formation_slug: str,
    support_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    formation = await _formation(db, formation_slug)
    support = (await db.execute(
        select(FormationSupport).where(FormationSupport.id == support_id, FormationSupport.formation_id == formation.id)
    )).scalars().first()
    if not support:
        raise HTTPException(status_code=404, detail="Support non trouvé.")
    chemin = support.chemin
    await db.delete(support)
    await db.commit()
    if chemin:
        try:
            os.remove(os.path.join(settings.UPLOAD_DIR, chemin))
        except OSError:
            pass
    return None


# ─────────────────────────────────────────────────────
# ÉVALUATION FINALE (QCM)
# ─────────────────────────────────────────────────────

class QuestionEcriture(BaseModel):
    enonce: str = Field(min_length=3)
    choix: List[str] = Field(min_length=2, max_length=8)
    bonnes_reponses: List[int] = Field(min_length=1)
    ordre: int = 0


class QuestionAdmin(QuestionEcriture):
    id: int


class QuestionParticipant(BaseModel):
    id: int
    enonce: str
    choix: List[str]
    plusieurs_reponses: bool


class TentativeRead(BaseModel):
    score: int
    reussi: bool
    date: str


class EvaluationParticipant(BaseModel):
    note_minimale: int
    questions: List[QuestionParticipant]
    lecons_terminees: bool
    reussie: bool
    tentatives: List[TentativeRead]
    certificat_code: Optional[str] = None


class SoumissionEvaluation(BaseModel):
    # {id de question: [index des choix cochés]}
    reponses: Dict[int, List[int]]


class ResultatEvaluation(BaseModel):
    score: int
    reussi: bool
    note_minimale: int
    bonnes: int
    total: int
    # Questions mal répondues (sans révéler la bonne réponse)
    questions_a_revoir: List[int]
    certificat_code: Optional[str] = None


class ReglagesEvaluation(BaseModel):
    note_minimale: int = Field(ge=0, le=100)


def _valider_question(q: QuestionEcriture) -> None:
    choix = [c.strip() for c in q.choix]
    if any(not c for c in choix):
        raise HTTPException(status_code=422, detail="Un choix de réponse est vide.")
    if any(i < 0 or i >= len(choix) for i in q.bonnes_reponses):
        raise HTTPException(status_code=422, detail="Bonne réponse invalide : elle doit désigner un des choix.")


def _question_admin(q: FormationQuestion) -> QuestionAdmin:
    return QuestionAdmin(
        id=q.id, enonce=q.enonce, choix=json.loads(q.choix),
        bonnes_reponses=json.loads(q.bonnes_reponses), ordre=q.ordre,
    )


async def _questions(db: AsyncSession, formation_id: int) -> List[FormationQuestion]:
    return (await db.execute(
        select(FormationQuestion)
        .where(FormationQuestion.formation_id == formation_id)
        .order_by(FormationQuestion.ordre, FormationQuestion.id)
    )).scalars().all()


@formation_parcours_router.get("/{formation_slug}/evaluation/questions", response_model=List[QuestionAdmin])
async def questions_admin(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Questions avec leurs bonnes réponses (staff)."""
    formation = await _formation(db, formation_slug)
    return [_question_admin(q) for q in await _questions(db, formation.id)]


@formation_parcours_router.post("/{formation_slug}/evaluation/questions", response_model=QuestionAdmin, status_code=201)
async def ajouter_question(
    formation_slug: str,
    payload: QuestionEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    formation = await _formation(db, formation_slug)
    _valider_question(payload)
    question = FormationQuestion(
        formation_id=formation.id, enonce=payload.enonce.strip(),
        choix=json.dumps([c.strip() for c in payload.choix], ensure_ascii=False),
        bonnes_reponses=json.dumps(sorted(set(payload.bonnes_reponses))), ordre=payload.ordre,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return _question_admin(question)


@formation_parcours_router.put("/{formation_slug}/evaluation/questions/{question_id}", response_model=QuestionAdmin)
async def modifier_question(
    formation_slug: str,
    question_id: int,
    payload: QuestionEcriture,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    formation = await _formation(db, formation_slug)
    question = (await db.execute(
        select(FormationQuestion).where(FormationQuestion.id == question_id, FormationQuestion.formation_id == formation.id)
    )).scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Question non trouvée.")
    _valider_question(payload)
    question.enonce = payload.enonce.strip()
    question.choix = json.dumps([c.strip() for c in payload.choix], ensure_ascii=False)
    question.bonnes_reponses = json.dumps(sorted(set(payload.bonnes_reponses)))
    question.ordre = payload.ordre
    await db.commit()
    await db.refresh(question)
    return _question_admin(question)


@formation_parcours_router.delete("/{formation_slug}/evaluation/questions/{question_id}", status_code=204)
async def supprimer_question(
    formation_slug: str,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    formation = await _formation(db, formation_slug)
    question = (await db.execute(
        select(FormationQuestion).where(FormationQuestion.id == question_id, FormationQuestion.formation_id == formation.id)
    )).scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Question non trouvée.")
    await db.delete(question)
    await db.commit()
    return None


@formation_parcours_router.patch("/{formation_slug}/evaluation", response_model=ReglagesEvaluation)
async def regler_evaluation(
    formation_slug: str,
    payload: ReglagesEvaluation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """Note minimale (en %) pour réussir l'évaluation (staff)."""
    formation = await _formation(db, formation_slug)
    formation.note_minimale = payload.note_minimale
    await db.commit()
    return ReglagesEvaluation(note_minimale=formation.note_minimale)


async def _inscription_avec_acces(db: AsyncSession, formation: Formation, user: User):
    inscription = await formation_acces.inscription_de(db, formation.id, user)
    if not inscription:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas inscrit à cette formation.")
    if not formation_acces.a_acces(inscription):
        raise HTTPException(status_code=403, detail="Votre paiement n'est pas encore validé.")
    return inscription


@formation_parcours_router.get("/{formation_slug}/evaluation", response_model=EvaluationParticipant)
async def evaluation_participant(
    formation_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Questions de l'évaluation (sans les réponses) et historique des tentatives."""
    formation = await _formation(db, formation_slug)
    inscription = await _inscription_avec_acces(db, formation, current_user)
    vues, total = await formation_acces.progression(db, formation.id, inscription.id)
    tentatives = (await db.execute(
        select(FormationTentative)
        .where(FormationTentative.inscription_id == inscription.id)
        .order_by(FormationTentative.created_at.desc())
    )).scalars().all()
    certificat = await formation_acces.certificat_de(db, inscription.id)
    return EvaluationParticipant(
        note_minimale=formation.note_minimale,
        questions=[
            QuestionParticipant(
                id=q.id, enonce=q.enonce, choix=json.loads(q.choix),
                plusieurs_reponses=len(json.loads(q.bonnes_reponses)) > 1,
            )
            for q in await _questions(db, formation.id)
        ],
        lecons_terminees=vues >= total,
        reussie=any(t.reussi for t in tentatives),
        tentatives=[TentativeRead(score=t.score, reussi=t.reussi, date=t.created_at.isoformat()) for t in tentatives],
        certificat_code=certificat.code if certificat else None,
    )


@formation_parcours_router.post("/{formation_slug}/evaluation", response_model=ResultatEvaluation)
async def passer_evaluation(
    formation_slug: str,
    payload: SoumissionEvaluation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Corrige l'évaluation. Une question est juste si exactement les bons choix
    sont cochés. Score >= note minimale : évaluation réussie et certificat
    délivré (toutes les leçons doivent avoir été suivies). Tentatives illimitées.
    """
    formation = await _formation(db, formation_slug)
    inscription = await _inscription_avec_acces(db, formation, current_user)
    questions = await _questions(db, formation.id)
    if not questions:
        raise HTTPException(status_code=400, detail="Cette formation n'a pas d'évaluation.")
    vues, total = await formation_acces.progression(db, formation.id, inscription.id)
    if vues < total:
        raise HTTPException(status_code=409, detail="Terminez d'abord toutes les leçons de la formation.")

    a_revoir = [
        q.id for q in questions
        if sorted(set(payload.reponses.get(q.id, []))) != json.loads(q.bonnes_reponses)
    ]
    bonnes = len(questions) - len(a_revoir)
    score = round(100 * bonnes / len(questions))
    reussi = score >= formation.note_minimale
    db.add(FormationTentative(
        inscription_id=inscription.id, score=score, reussi=reussi,
        reponses=json.dumps({str(k): v for k, v in payload.reponses.items()}),
    ))
    await db.flush()
    certificat = await formation_acces.delivrer_certificat_si_eligible(db, formation, inscription) if reussi else None
    await db.commit()
    if certificat:
        await db.refresh(certificat)
        await send_certificat_emis(
            participant_name=inscription.participant_name,
            participant_email=inscription.participant_email,
            formation_title=formation.title,
            cert_code=certificat.code,
        )
    existant = certificat or await formation_acces.certificat_de(db, inscription.id)
    return ResultatEvaluation(
        score=score, reussi=reussi, note_minimale=formation.note_minimale,
        bonnes=bonnes, total=len(questions), questions_a_revoir=a_revoir,
        certificat_code=existant.code if existant else None,
    )
