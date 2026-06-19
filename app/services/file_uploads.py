import os
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile

from app.core.config import settings


FORMALISATION_ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"}
FORMALISATION_FILE_MAX_SIZE = 10 * 1024 * 1024


def save_supporting_document(
    file: Optional[UploadFile],
    field_name: str,
    relative_dir: str = "osc-justificatifs",
) -> Optional[str]:
    if not file or not file.filename:
        return None

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in FORMALISATION_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "validation_error",
                "errors": [
                    {
                        "field": field_name,
                        "message": (
                            "Format invalide. Formats acceptés: "
                            f"{', '.join(sorted(FORMALISATION_ALLOWED_EXTENSIONS))}."
                        ),
                    }
                ],
            },
        )

    upload_dir = os.path.join(settings.UPLOAD_DIR, relative_dir)
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.{file_extension}"
    relative_path = f"{relative_dir}/{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
    bytes_written = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > FORMALISATION_FILE_MAX_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "type": "validation_error",
                            "errors": [
                                {
                                    "field": field_name,
                                    "message": "Le fichier ne doit pas dépasser 10 Mo.",
                                }
                            ],
                        },
                    )
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return relative_path


def save_formalisation_file(file: Optional[UploadFile]) -> Optional[str]:
    return save_supporting_document(
        file,
        field_name="document_formalisation_file",
        relative_dir="osc-formalisation",
    )
