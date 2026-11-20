# services/journal.py | Enregistrement des actions du back-office
import logging
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.journal import JournalAction
from app.models.users import User

logger = logging.getLogger(__name__)


# Libellés affichés dans l'historique. La clé est le code stocké en base.
LIBELLES_ACTIONS = {
    # Actualités
    "actualite_publiee": "Actualité publiée",
    "actualite_rejetee": "Actualité rejetée",
    "actualite_creee": "Actualité créée",
    "actualite_modifiee": "Actualité modifiée",
    "actualite_supprimee": "Actualité supprimée",
    # Adhésions / OSC
    "adhesion_approuvee": "Demande d'adhésion approuvée",
    "adhesion_rejetee": "Demande d'adhésion rejetée",
    "adhesion_supprimee": "Demande d'adhésion supprimée",
    "osc_creee": "OSC créée",
    "osc_modifiee": "OSC modifiée",
    "osc_supprimee": "OSC supprimée",
    "osc_visibilite": "Visibilité d'une OSC modifiée",
    # Offres d'emploi
    "offre_publiee": "Offre d'emploi publiée",
    "offre_rejetee": "Offre d'emploi rejetée",
    "offre_desactivee": "Offre d'emploi désactivée",
    "offre_activee": "Offre d'emploi réactivée",
    "offre_supprimee": "Offre d'emploi supprimée",
    # Formations et paiements
    "paiement_valide": "Paiement validé",
    "paiement_rejete": "Paiement rejeté",
    "inscription_supprimee": "Inscription supprimée",
    "paiements_reinitialises": "Liste des paiements réinitialisée",
    # Contact et messages
    "contact_reponse": "Réponse à un message de contact",
    "message_groupe_envoye": "Message groupé envoyé",
    # Comptes
    "compte_cree": "Compte créé",
    "compte_modifie": "Compte modifié",
    "compte_supprime": "Compte supprimé",
    # Exports
    "export_osc": "Export Excel de l'annuaire",
}


def libelle_action(code: str) -> str:
    return LIBELLES_ACTIONS.get(code, code.replace("_", " ").capitalize())


async def journaliser(
    db: AsyncSession,
    user: Optional[User],
    *,
    action: str,
    cible_type: Optional[str] = None,
    cible_id: Optional[str] = None,
    cible_libelle: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """Enregistre une action dans l'historique.

    Ne lève jamais : une trace manquante ne doit pas faire échouer l'action
    métier qui vient d'être réalisée.
    """
    try:
        identite = None
        if user is not None:
            nom = (user.full_name or "").strip() or user.username or ""
            identite = f"{nom} ({user.email})" if nom else user.email
        db.add(
            JournalAction(
                user_id=getattr(user, "id", None),
                utilisateur=identite,
                action=action,
                cible_type=cible_type,
                cible_id=str(cible_id) if cible_id is not None else None,
                cible_libelle=(cible_libelle or None) and str(cible_libelle)[:300],
                details=details,
            )
        )
        await db.commit()
    except Exception as exc:  # pragma: no cover - trace best effort
        logger.error("Journalisation impossible (%s) : %s", action, exc)
        try:
            await db.rollback()
        except Exception:
            pass
