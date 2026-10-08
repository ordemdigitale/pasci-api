# services/formation_acces.py
"""
Règles d'accès et de certification des formations, partagées par tous les
endpoints (une seule définition, pour qu'aucun écran ne s'en écarte) :

- accès au contenu (leçons non « aperçu », supports réservés, évaluation) :
  inscription gratuite ou paiement validé. Un paiement « en attente » ou
  « soumis » (code Wave / Orange en cours de vérification) ne donne pas accès ;
- certificat : toutes les leçons suivies ET, si la formation comporte une
  évaluation finale, une tentative réussie (score >= note minimale).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.formation import (
    Certificat,
    Formation,
    FormationInscription,
    FormationLecon,
    FormationModule,
    FormationProgression,
    FormationQuestion,
    FormationTentative,
)
from app.models.users import User

# « paid » : ancien libellé, conservé pour les inscriptions déjà en base
STATUTS_AVEC_ACCES = {"gratuite", "confirmed", "paid"}


def _maintenant(reference: datetime) -> datetime:
    return datetime.now(reference.tzinfo) if reference.tzinfo else datetime.now()


def est_terminee(formation) -> bool:
    """Cochée « terminée » ou date de fin (à défaut, de début) passée."""
    if formation.is_completed:
        return True
    fin = formation.end_date or formation.start_date
    return bool(fin and fin < _maintenant(fin))


def inscriptions_ouvertes(formation) -> bool:
    """Non terminée, non complète et date limite d'inscription non dépassée."""
    if est_terminee(formation) or formation.is_full:
        return False
    limite = formation.registration_deadline
    return not limite or limite >= _maintenant(limite)


def est_staff(user: Optional[User]) -> bool:
    return bool(user and (user.is_staff or user.is_superuser))


def a_acces(inscription: Optional[FormationInscription]) -> bool:
    return bool(inscription and inscription.payment_status in STATUTS_AVEC_ACCES)


async def inscription_de(db: AsyncSession, formation_id: int, user: Optional[User]) -> Optional[FormationInscription]:
    """Inscription de l'utilisateur (par compte, sinon par email sans tenir compte de la casse)."""
    if not user:
        return None
    rows = (await db.execute(
        select(FormationInscription).where(
            FormationInscription.formation_id == formation_id,
            (FormationInscription.user_id == user.id)
            | (func.lower(func.btrim(FormationInscription.participant_email)) == (user.email or "").strip().lower()),
        ).order_by(FormationInscription.id)
    )).scalars().all()
    # Priorité à une inscription qui donne accès (doublons éventuels)
    return next((i for i in rows if a_acces(i)), rows[0] if rows else None)


async def progression(db: AsyncSession, formation_id: int, inscription_id: int) -> tuple:
    """(leçons vues, total des leçons) de la formation."""
    total = (await db.execute(
        select(func.count(FormationLecon.id))
        .join(FormationModule, FormationLecon.module_id == FormationModule.id)
        .where(FormationModule.formation_id == formation_id)
    )).scalar() or 0
    vues = (await db.execute(
        select(func.count(func.distinct(FormationProgression.lecon_id)))
        .join(FormationLecon, FormationLecon.id == FormationProgression.lecon_id)
        .join(FormationModule, FormationLecon.module_id == FormationModule.id)
        .where(FormationProgression.inscription_id == inscription_id, FormationModule.formation_id == formation_id)
    )).scalar() or 0
    return vues, total


async def nombre_questions(db: AsyncSession, formation_id: int) -> int:
    return (await db.execute(
        select(func.count(FormationQuestion.id)).where(FormationQuestion.formation_id == formation_id)
    )).scalar() or 0


async def evaluation_reussie(db: AsyncSession, inscription_id: int) -> bool:
    return bool((await db.execute(
        select(func.count(FormationTentative.id)).where(
            FormationTentative.inscription_id == inscription_id, FormationTentative.reussi == True  # noqa: E712
        )
    )).scalar())


async def certificat_de(db: AsyncSession, inscription_id: int) -> Optional[Certificat]:
    return (await db.execute(
        select(Certificat).where(Certificat.inscription_id == inscription_id)
    )).scalars().first()


async def delivrer_certificat_si_eligible(
    db: AsyncSession, formation: Formation, inscription: FormationInscription
) -> Optional[Certificat]:
    """
    Marque l'inscription complétée et émet le certificat si les conditions
    sont réunies. Retourne le certificat NOUVELLEMENT émis (None sinon).
    Ne commit pas.
    """
    if not a_acces(inscription):
        return None
    vues, total = await progression(db, formation.id, inscription.id)
    lecons_ok = vues >= total  # une formation sans leçon n'est validée que par l'évaluation
    nb_q = await nombre_questions(db, formation.id)
    if total == 0 and nb_q == 0:
        return None
    if not lecons_ok:
        return None
    if nb_q > 0 and not await evaluation_reussie(db, inscription.id):
        return None

    if not inscription.is_completed:
        inscription.is_completed = True
        inscription.completed_at = datetime.utcnow()
    if inscription.certificate_issued or await certificat_de(db, inscription.id):
        inscription.certificate_issued = True
        return None
    certificat = Certificat(
        inscription_id=inscription.id,
        formation_title=formation.title,
        participant_name=inscription.participant_name,
        participant_email=inscription.participant_email,
    )
    db.add(certificat)
    inscription.certificate_issued = True
    return certificat
