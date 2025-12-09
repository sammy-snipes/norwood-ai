"""Certification service for managing premium certifications."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Certification,
    CertificationPhoto,
    CertificationStatus,
    PhotoType,
    User,
    ValidationStatus,
)
from app.services.s3 import S3Service

logger = logging.getLogger(__name__)
settings = get_settings()


def check_cooldown(user: User, db: Session) -> int | None:
    """
    Check if user can create a new certification.

    Returns days remaining if on cooldown, None if can certify.
    Currently disabled - unlimited certifications allowed.
    """
    return None


def get_or_create(user: User, db: Session) -> tuple[Certification, bool]:
    """
    Get existing incomplete certification or create new one.

    Returns tuple of (certification, is_new).
    """
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
        return incomplete, False

    # Create new certification
    certification = Certification(user_id=user.id)
    db.add(certification)
    db.commit()
    db.refresh(certification)
    logger.info(f"Created new certification {certification.id} for user {user.id}")

    return certification, True


def get_by_id(cert_id: str, user: User, db: Session) -> Certification | None:
    """Get certification by ID for the given user."""
    return (
        db.query(Certification)
        .filter(
            Certification.id == cert_id,
            Certification.user_id == user.id,
        )
        .first()
    )


def prepare_photo_upload(
    certification: Certification,
    photo_type: PhotoType,
    db: Session,
) -> tuple[CertificationPhoto | None, str | None]:
    """
    Prepare for photo upload by handling existing photos.

    Returns tuple of (new_photo, error_message).
    If error_message is set, the upload should be rejected.
    """
    if certification.status != CertificationStatus.photos_pending:
        return None, "Certification is not accepting photos"

    # Check if photo type already exists and is approved
    existing = (
        db.query(CertificationPhoto)
        .filter(
            CertificationPhoto.certification_id == certification.id,
            CertificationPhoto.photo_type == photo_type,
        )
        .first()
    )

    if existing and existing.validation_status == ValidationStatus.approved:
        return None, f"{photo_type.value} photo already approved"

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
        certification_id=certification.id,
        photo_type=photo_type,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    return photo, None


def get_status(certification: Certification) -> dict:
    """Get certification status with photo details and presigned URLs."""
    photos = [
        {
            "photo_id": p.id,
            "photo_type": p.photo_type.value,
            "validation_status": p.validation_status.value,
            "rejection_reason": p.rejection_reason,
            "quality_notes": p.quality_notes,
        }
        for p in certification.photos
    ]

    pdf_url = None
    if certification.pdf_s3_key:
        try:
            s3 = S3Service()
            pdf_url = s3.get_presigned_url(certification.pdf_s3_key)
        except Exception:
            pass

    return {
        "certification_id": certification.id,
        "status": certification.status.value,
        "photos": photos,
        "norwood_stage": certification.norwood_stage,
        "norwood_variant": certification.norwood_variant,
        "confidence": certification.confidence,
        "clinical_assessment": certification.clinical_assessment,
        "pdf_url": pdf_url,
        "certified_at": certification.certified_at,
    }


def validate_can_diagnose(certification: Certification) -> str | None:
    """
    Check if certification is ready for diagnosis.

    Returns error message if not ready, None if ready.
    """
    if certification.status != CertificationStatus.photos_pending:
        return "Certification already processing or complete"

    # Check all photos are approved
    approved_types = {
        p.photo_type
        for p in certification.photos
        if p.validation_status == ValidationStatus.approved
    }
    required = {PhotoType.front, PhotoType.left, PhotoType.right}

    if approved_types != required:
        missing = required - approved_types
        return f"Missing approved photos: {[t.value for t in missing]}"

    return None


def get_pdf_url(certification: Certification, expires_in: int = 3600) -> str | None:
    """Get presigned URL for PDF download."""
    if not certification.pdf_s3_key:
        return None

    s3 = S3Service()
    return s3.get_presigned_url(certification.pdf_s3_key, expires_in=expires_in)


def get_history(user: User, db: Session) -> list[dict]:
    """Get user's completed certification history with presigned URLs."""
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
    result = []
    for c in certifications:
        pdf_url = None
        if c.pdf_s3_key:
            try:
                pdf_url = s3.get_presigned_url(c.pdf_s3_key)
            except Exception:
                pass
        result.append(
            {
                "id": c.id,
                "norwood_stage": c.norwood_stage,
                "norwood_variant": c.norwood_variant,
                "certified_at": c.certified_at,
                "pdf_url": pdf_url,
            }
        )

    return result


def get_public_info(cert_id: str, db: Session) -> dict | None:
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
        return None

    return {
        "norwood_stage": certification.norwood_stage,
        "norwood_variant": certification.norwood_variant,
        "certified_at": certification.certified_at,
    }


def delete_with_cleanup(cert_id: str, user: User, db: Session) -> bool:
    """Delete a certification and all associated S3 assets."""
    certification = get_by_id(cert_id, user, db)

    if not certification:
        return False

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
    logger.info(f"Deleted certification {cert_id}")

    return True
