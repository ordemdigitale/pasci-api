# services/forum_medias.py
"""
Pièces jointes des messages des pôles de concertation : photos, audio, vidéos.

Les fichiers sont stockés sous UPLOAD_DIR/forum/ et servis via /static/forum/.
Le type est déterminé par l'extension et vérifié contre le type MIME annoncé ;
la taille est contrôlée pendant l'écriture (un fichier trop gros est rejeté
sans être chargé entièrement en mémoire). Limites : settings.FORUM_MAX_*.
"""
import os
import uuid
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.forum import ForumPieceJointe

DOSSIER = "forum"
TAILLE_BLOC = 1024 * 1024

EXTENSIONS = {
    "image": {"jpg", "jpeg", "png", "webp"},
    "audio": {"mp3", "m4a", "aac", "ogg", "oga", "wav", "webm", "opus", "3gp"},
    "video": {"mp4", "mov", "webm", "3gp", "m4v"},
}
LIBELLES = {"image": "photo", "audio": "audio", "video": "vidéo"}


def limites_mo() -> dict:
    return {
        "image": settings.FORUM_MAX_IMAGE_MO,
        "audio": settings.FORUM_MAX_AUDIO_MO,
        "video": settings.FORUM_MAX_VIDEO_MO,
        "fichiers": settings.FORUM_MAX_FICHIERS,
    }


def _type_fichier(fichier: UploadFile) -> str:
    """image | audio | video, d'après le type MIME puis l'extension."""
    nom = fichier.filename or ""
    extension = nom.rsplit(".", 1)[-1].lower() if "." in nom else ""
    mime = (fichier.content_type or "").lower()
    famille = mime.split("/")[0] if "/" in mime else ""
    if famille in EXTENSIONS and extension in EXTENSIONS[famille]:
        return famille
    # Certains téléphones envoient application/octet-stream : on se fie à l'extension
    if famille in ("", "application"):
        for type_, extensions in EXTENSIONS.items():
            if extension in extensions and extension != "webm":
                return type_
    formats = ", ".join(sorted(EXTENSIONS["image"] | EXTENSIONS["audio"] | EXTENSIONS["video"]))
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"« {nom} » : format non accepté. Formats acceptés : {formats}.",
    )


async def enregistrer_fichiers(fichiers: List[UploadFile]) -> List[ForumPieceJointe]:
    """
    Valide et enregistre les fichiers ; retourne les pièces jointes (non
    rattachées, non ajoutées à la session). En cas d'erreur, les fichiers
    déjà écrits sont supprimés.
    """
    fichiers = [f for f in fichiers or [] if f and f.filename]
    if len(fichiers) > settings.FORUM_MAX_FICHIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{settings.FORUM_MAX_FICHIERS} fichiers au maximum par message.",
        )
    dossier = os.path.join(settings.UPLOAD_DIR, DOSSIER)
    os.makedirs(dossier, exist_ok=True)
    pieces: List[ForumPieceJointe] = []
    try:
        for fichier in fichiers:
            type_ = _type_fichier(fichier)
            max_octets = limites_mo()[type_] * 1024 * 1024
            extension = fichier.filename.rsplit(".", 1)[-1].lower()
            nom_stocke = f"{uuid.uuid4().hex}.{extension}"
            chemin_disque = os.path.join(dossier, nom_stocke)
            taille = 0
            with open(chemin_disque, "wb") as sortie:
                while True:
                    bloc = await fichier.read(TAILLE_BLOC)
                    if not bloc:
                        break
                    taille += len(bloc)
                    if taille > max_octets:
                        sortie.close()
                        os.remove(chemin_disque)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=(
                                f"« {fichier.filename} » dépasse la taille autorisée pour une "
                                f"{LIBELLES[type_]} ({limites_mo()[type_]} Mo)."
                            ),
                        )
                    sortie.write(bloc)
            pieces.append(ForumPieceJointe(
                type=type_,
                chemin=f"{DOSSIER}/{nom_stocke}",
                nom_original=fichier.filename[:255],
                mime=(fichier.content_type or "")[:100] or None,
                taille=taille,
            ))
    except Exception:
        supprimer_fichiers(pieces)
        raise
    return pieces


def supprimer_fichiers(pieces: List[ForumPieceJointe]) -> None:
    for piece in pieces:
        try:
            os.remove(os.path.join(settings.UPLOAD_DIR, piece.chemin))
        except OSError:
            pass


def serialiser(piece: ForumPieceJointe) -> dict:
    return {
        "id": piece.id,
        "type": piece.type,
        "url": f"{settings.API_BASE_URL}/static/{piece.chemin}",
        "nom": piece.nom_original,
        "mime": piece.mime,
        "taille": piece.taille,
    }
