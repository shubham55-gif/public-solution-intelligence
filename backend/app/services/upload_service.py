"""Safe filesystem handling for optional report image uploads."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import MAX_IMAGE_SIZE_BYTES, UPLOADS_DIR


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg", "application/octet-stream"}
REPORT_IMAGES_DIR = UPLOADS_DIR / "reports"


async def save_report_image(upload: UploadFile) -> tuple[str, Path]:
    """Save an image under a generated name and return its logical reference/path."""
    original_name = upload.filename or ""
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS or upload.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image must be a JPG, PNG, or WEBP file",
        )

    REPORT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    destination = (REPORT_IMAGES_DIR / f"{uuid4().hex}{suffix}").resolve()
    uploads_root = UPLOADS_DIR.resolve()
    if not destination.is_relative_to(uploads_root):
        raise HTTPException(status_code=400, detail="Invalid upload destination")

    bytes_written = 0
    try:
        with destination.open("xb") as output:
            while chunk := await upload.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > MAX_IMAGE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Image exceeds the configured size limit",
                    )
                output.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not save uploaded image") from exc
    finally:
        await upload.close()

    return f"uploads/reports/{destination.name}", destination
