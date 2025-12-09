"""Cock certification service for managing premium cock certifications."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CockCertification, CockCertificationStatus, User
from app.services.s3 import S3Service

logger = logging.getLogger(__name__)
settings = get_settings()


def create_certification(user: User, db: Session) -> CockCertification:
    """Create a new cock certification record."""
    certification = CockCertification(user_id=user.id)
    db.add(certification)
    db.commit()
    db.refresh(certification)
    logger.info(f"Created cock certification {certification.id} for user {user.id}")
    return certification


def get_by_id(cert_id: str, user: User, db: Session) -> CockCertification | None:
    """Get certification by ID for the given user."""
    return (
        db.query(CockCertification)
        .filter(
            CockCertification.id == cert_id,
            CockCertification.user_id == user.id,
        )
        .first()
    )


def get_status(certification: CockCertification) -> dict:
    """Get certification status with presigned URLs."""
    pdf_url = None
    if certification.pdf_s3_key:
        try:
            s3 = S3Service()
            pdf_url = s3.get_presigned_url(certification.pdf_s3_key)
        except Exception:
            pass

    return {
        "id": certification.id,
        "status": certification.status.value,
        "length_inches": certification.length_inches,
        "girth_inches": certification.girth_inches,
        "size_category": certification.size_category.value if certification.size_category else None,
        "pleasure_zone": certification.pleasure_zone.name if certification.pleasure_zone else None,
        "pleasure_zone_label": certification.pleasure_zone_label,
        "description": certification.description,
        "confidence": certification.confidence,
        "reference_objects_used": certification.reference_objects_used,
        "pdf_url": pdf_url,
        "certified_at": certification.certified_at,
    }


def get_pdf_url(certification: CockCertification, expires_in: int = 3600) -> str | None:
    """Get presigned URL for PDF download."""
    if not certification.pdf_s3_key:
        return None

    s3 = S3Service()
    return s3.get_presigned_url(certification.pdf_s3_key, expires_in=expires_in)


def get_history(user: User, db: Session) -> list[dict]:
    """Get user's completed cock certification history with presigned URLs."""
    certifications = (
        db.query(CockCertification)
        .filter(
            CockCertification.user_id == user.id,
            CockCertification.status == CockCertificationStatus.completed,
        )
        .order_by(CockCertification.certified_at.desc())
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
                "length_inches": c.length_inches,
                "girth_inches": c.girth_inches,
                "size_category": c.size_category.value if c.size_category else None,
                "pleasure_zone": c.pleasure_zone.name if c.pleasure_zone else None,
                "pleasure_zone_label": c.pleasure_zone_label,
                "certified_at": c.certified_at,
                "pdf_url": pdf_url,
            }
        )

    return result


def get_public_info(cert_id: str, db: Session) -> dict | None:
    """Get public certification info (no auth required)."""
    certification = (
        db.query(CockCertification)
        .filter(
            CockCertification.id == cert_id,
            CockCertification.status == CockCertificationStatus.completed,
        )
        .first()
    )

    if not certification:
        return None

    return {
        "length_inches": certification.length_inches,
        "girth_inches": certification.girth_inches,
        "size_category": certification.size_category.value if certification.size_category else None,
        "pleasure_zone": certification.pleasure_zone.name if certification.pleasure_zone else None,
        "pleasure_zone_label": certification.pleasure_zone_label,
        "certified_at": certification.certified_at,
    }


def delete_with_cleanup(cert_id: str, user: User, db: Session) -> bool:
    """Delete a certification and all associated S3 assets."""
    certification = get_by_id(cert_id, user, db)

    if not certification:
        return False

    s3 = S3Service()

    # Delete image from S3
    if certification.s3_key:
        try:
            s3.delete_image(certification.s3_key)
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
    logger.info(f"Deleted cock certification {cert_id}")

    return True
