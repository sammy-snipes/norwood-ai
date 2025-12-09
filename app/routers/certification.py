"""Certification router - premium only."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PhotoType, User
from app.routers.auth import decode_token
from app.services import certification as certification_service
from app.tasks.certification import (
    generate_certification_diagnosis_task,
    validate_certification_photo_task,
)

router = APIRouter(prefix="/api/certification", tags=["certification"])


# Schemas
class StartCertificationResponse(BaseModel):
    certification_id: str
    status: str


class PhotoUploadRequest(BaseModel):
    image_base64: str
    content_type: str


class PhotoUploadResponse(BaseModel):
    photo_id: str
    task_id: str


class PhotoStatusResponse(BaseModel):
    photo_id: str
    photo_type: str
    validation_status: str
    rejection_reason: str | None
    quality_notes: str | None


class CertificationStatusResponse(BaseModel):
    certification_id: str
    status: str
    photos: list[PhotoStatusResponse]
    norwood_stage: int | None
    norwood_variant: str | None
    confidence: float | None
    clinical_assessment: str | None
    pdf_url: str | None
    certified_at: datetime | None


class DiagnoseResponse(BaseModel):
    task_id: str


class CertificationHistoryItem(BaseModel):
    id: str
    norwood_stage: int | None
    norwood_variant: str | None
    certified_at: datetime | None
    pdf_url: str | None


# Dependencies
def require_premium(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Require premium or admin user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_premium and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Certification requires a premium subscription",
        )

    return user


# Routes
@router.get("/cooldown")
def get_cooldown(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Check if user is on certification cooldown."""
    days_remaining = certification_service.check_cooldown(user, db)
    return {
        "on_cooldown": days_remaining is not None and days_remaining > 0,
        "days_remaining": days_remaining if days_remaining and days_remaining > 0 else 0,
    }


@router.post("/start", response_model=StartCertificationResponse)
def start_certification(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Start a new certification process."""
    days_remaining = certification_service.check_cooldown(user, db)
    if days_remaining is not None and days_remaining > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You can only certify once per month. {days_remaining} days remaining.",
        )

    certification, _ = certification_service.get_or_create(user, db)
    return StartCertificationResponse(
        certification_id=certification.id,
        status=certification.status.value,
    )


@router.post("/{cert_id}/photo/{photo_type}", response_model=PhotoUploadResponse)
def upload_photo(
    cert_id: str,
    photo_type: PhotoType,
    request: PhotoUploadRequest,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Upload and validate a certification photo."""
    certification = certification_service.get_by_id(cert_id, user, db)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    photo, error = certification_service.prepare_photo_upload(certification, photo_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Queue validation task (processes image, uploads to S3, validates)
    task = validate_certification_photo_task.delay(
        photo.id,
        request.image_base64,
        request.content_type,
        photo_type.value,
        user.id,
        cert_id,
    )

    return PhotoUploadResponse(photo_id=photo.id, task_id=task.id)


@router.get("/{cert_id}/status", response_model=CertificationStatusResponse)
def get_certification_status(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get current certification status."""
    certification = certification_service.get_by_id(cert_id, user, db)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    status_data = certification_service.get_status(certification)
    return CertificationStatusResponse(
        **{
            **status_data,
            "photos": [PhotoStatusResponse(**p) for p in status_data["photos"]],
        }
    )


@router.post("/{cert_id}/diagnose", response_model=DiagnoseResponse)
def trigger_diagnosis(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Trigger final diagnosis after all photos are approved."""
    certification = certification_service.get_by_id(cert_id, user, db)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    error = certification_service.validate_can_diagnose(certification)
    if error:
        raise HTTPException(status_code=400, detail=error)

    task = generate_certification_diagnosis_task.delay(certification.id)
    return DiagnoseResponse(task_id=task.id)


@router.get("/{cert_id}/pdf")
def download_pdf(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get presigned URL for PDF download."""
    certification = certification_service.get_by_id(cert_id, user, db)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    pdf_url = certification_service.get_pdf_url(certification)
    if not pdf_url:
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    return {"pdf_url": pdf_url}


@router.get("/history", response_model=list[CertificationHistoryItem])
def get_certification_history(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get user's certification history."""
    history = certification_service.get_history(user, db)
    return [CertificationHistoryItem(**item) for item in history]


@router.get("/public/{cert_id}")
def get_public_certification(
    cert_id: str,
    db: Session = Depends(get_db),
):
    """Get public certification info (no auth required)."""
    info = certification_service.get_public_info(cert_id, db)
    if not info:
        raise HTTPException(status_code=404, detail="Certification not found")
    return info


@router.delete("/{cert_id}")
def delete_certification(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Delete a certification."""
    deleted = certification_service.delete_with_cleanup(cert_id, user, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Certification not found")
    return {"success": True}
