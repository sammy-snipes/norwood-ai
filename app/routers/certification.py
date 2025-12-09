"""Certification router - premium only."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Certification,
    CertificationPhoto,
    CertificationStatus,
    PhotoType,
    User,
    ValidationStatus,
)
from app.routers.auth import decode_token
from app.services.s3 import S3Service
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


def check_certification_cooldown(user: User, db: Session) -> int | None:
    """
    Check if user can create a new certification.

    Returns days remaining if on cooldown, None if can certify.
    Currently disabled - unlimited certifications allowed.
    """
    return None


# Routes
@router.get("/cooldown")
def get_cooldown(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Check if user is on certification cooldown."""
    days_remaining = check_certification_cooldown(user, db)
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
    days_remaining = check_certification_cooldown(user, db)
    if days_remaining is not None and days_remaining > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You can only certify once per month. {days_remaining} days remaining.",
        )

    # Check for incomplete certifications
    incomplete = (
        db.query(Certification)
        .filter(
            Certification.user_id == user.id,
            Certification.status.in_(
                [
                    CertificationStatus.photos_pending,
                    CertificationStatus.analyzing,
                ]
            ),
        )
        .first()
    )

    if incomplete:
        # Return existing incomplete certification
        return StartCertificationResponse(
            certification_id=incomplete.id,
            status=incomplete.status.value,
        )

    # Create new certification
    certification = Certification(user_id=user.id)
    db.add(certification)
    db.commit()
    db.refresh(certification)

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
    certification = (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    if certification.status != CertificationStatus.photos_pending:
        raise HTTPException(status_code=400, detail="Certification is not accepting photos")

    # Check if photo type already exists and is approved
    existing = (
        db.query(CertificationPhoto)
        .filter(
            CertificationPhoto.certification_id == cert_id,
            CertificationPhoto.photo_type == photo_type,
        )
        .first()
    )

    if existing and existing.validation_status == ValidationStatus.approved:
        raise HTTPException(
            status_code=400,
            detail=f"{photo_type.value} photo already approved",
        )

    # Delete existing photo if retaking
    if existing:
        try:
            s3 = S3Service()
            s3.delete_image(existing.s3_key)
        except Exception:
            pass
        db.delete(existing)
        db.commit()

    # Create photo record (s3_key will be set by the task after processing)
    photo = CertificationPhoto(
        certification_id=cert_id,
        photo_type=photo_type,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    # Queue validation task (processes image, uploads to S3, validates)
    task = validate_certification_photo_task.delay(
        photo.id,
        request.image_base64,
        request.content_type,
        photo_type.value,
        user.id,
        cert_id,
    )

    return PhotoUploadResponse(
        photo_id=photo.id,
        task_id=task.id,
    )


@router.get("/{cert_id}/status", response_model=CertificationStatusResponse)
def get_certification_status(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get current certification status."""
    certification = (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    photos = [
        PhotoStatusResponse(
            photo_id=p.id,
            photo_type=p.photo_type.value,
            validation_status=p.validation_status.value,
            rejection_reason=p.rejection_reason,
            quality_notes=p.quality_notes,
        )
        for p in certification.photos
    ]

    pdf_url = None
    if certification.pdf_s3_key:
        try:
            s3 = S3Service()
            pdf_url = s3.get_presigned_url(certification.pdf_s3_key)
        except Exception:
            pass

    return CertificationStatusResponse(
        certification_id=certification.id,
        status=certification.status.value,
        photos=photos,
        norwood_stage=certification.norwood_stage,
        norwood_variant=certification.norwood_variant,
        confidence=certification.confidence,
        clinical_assessment=certification.clinical_assessment,
        pdf_url=pdf_url,
        certified_at=certification.certified_at,
    )


@router.post("/{cert_id}/diagnose", response_model=DiagnoseResponse)
def trigger_diagnosis(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Trigger final diagnosis after all photos are approved."""
    certification = (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    if certification.status != CertificationStatus.photos_pending:
        raise HTTPException(status_code=400, detail="Certification already processing or complete")

    # Check all photos are approved
    approved_types = {
        p.photo_type
        for p in certification.photos
        if p.validation_status == ValidationStatus.approved
    }
    required = {PhotoType.front, PhotoType.left, PhotoType.right}

    if approved_types != required:
        missing = required - approved_types
        raise HTTPException(
            status_code=400,
            detail=f"Missing approved photos: {[t.value for t in missing]}",
        )

    # Queue diagnosis task
    task = generate_certification_diagnosis_task.delay(certification.id)

    return DiagnoseResponse(task_id=task.id)


@router.get("/{cert_id}/pdf")
def download_pdf(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get presigned URL for PDF download."""
    certification = (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    if not certification.pdf_s3_key:
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    s3 = S3Service()
    url = s3.get_presigned_url(certification.pdf_s3_key, expires_in=3600)
    return {"pdf_url": url}


@router.get("/history", response_model=list[CertificationHistoryItem])
def get_certification_history(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get user's certification history."""
    certifications = (
        db.query(Certification)
        .filter(
            Certification.user_id == user.id,
            Certification.status == CertificationStatus.completed,
        )
        .order_by(Certification.certified_at.desc())
        .all()
    )

    s3 = S3Service()
    return [
        CertificationHistoryItem(
            id=c.id,
            norwood_stage=c.norwood_stage,
            norwood_variant=c.norwood_variant,
            certified_at=c.certified_at,
            pdf_url=s3.get_presigned_url(c.pdf_s3_key) if c.pdf_s3_key else None,
        )
        for c in certifications
    ]


@router.get("/public/{cert_id}")
def get_public_certification(
    cert_id: str,
    db: Session = Depends(get_db),
):
    """Get public certification info (no auth required)."""
    certification = (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.status == CertificationStatus.completed,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    return {
        "norwood_stage": certification.norwood_stage,
        "norwood_variant": certification.norwood_variant,
        "certified_at": certification.certified_at,
    }


@router.delete("/{cert_id}")
def delete_certification(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Delete a certification."""
    certification = (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    # Delete photos from S3
    s3 = S3Service()
    for photo in certification.photos:
        try:
            s3.delete_image(photo.s3_key)
        except Exception:
            pass

    # Delete PDF if exists
    if certification.pdf_s3_key:
        try:
            s3.delete_image(certification.pdf_s3_key)
        except Exception:
            pass

    db.delete(certification)
    db.commit()

    return {"success": True}
