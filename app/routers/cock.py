"""Cock certification router - premium only."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CockCertification, CockCertificationStatus, User
from app.routers.auth import decode_token
from app.services.s3 import S3Service
from app.tasks.cock import analyze_cock_task

router = APIRouter(prefix="/api/cock", tags=["cock"])


# Schemas
class SubmitPhotoRequest(BaseModel):
    image_base64: str
    content_type: str


class SubmitPhotoResponse(BaseModel):
    certification_id: str
    task_id: str


class CockCertificationResponse(BaseModel):
    id: str
    status: str
    length_inches: float | None
    girth_inches: float | None
    size_category: str | None
    pleasure_zone: str | None
    pleasure_zone_label: str | None
    description: str | None
    confidence: float | None
    reference_objects_used: str | None
    pdf_url: str | None
    certified_at: datetime | None


class CockHistoryItem(BaseModel):
    id: str
    length_inches: float | None
    girth_inches: float | None
    size_category: str | None
    pleasure_zone: str | None
    pleasure_zone_label: str | None
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
            detail="Cock certification requires a premium subscription",
        )

    return user


# Routes
@router.post("/submit", response_model=SubmitPhotoResponse)
def submit_photo(
    request: SubmitPhotoRequest,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Submit a cock photo for certification."""
    # Upload to S3
    s3 = S3Service()
    s3_key = s3.upload_base64_image_with_prefix(
        request.image_base64,
        user.id,
        request.content_type,
        "cock_certifications",
    )

    # Create certification record
    certification = CockCertification(
        user_id=user.id,
        s3_key=s3_key,
    )
    db.add(certification)
    db.commit()
    db.refresh(certification)

    # Queue analysis task
    task = analyze_cock_task.delay(
        certification.id,
        request.image_base64,
        request.content_type,
    )

    return SubmitPhotoResponse(
        certification_id=certification.id,
        task_id=task.id,
    )


@router.get("/{cert_id}", response_model=CockCertificationResponse)
def get_certification(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get certification status and results."""
    certification = (
        db.query(CockCertification)
        .filter(
            CockCertification.id == cert_id,
            CockCertification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    pdf_url = None
    if certification.pdf_s3_key:
        try:
            s3 = S3Service()
            pdf_url = s3.get_presigned_url(certification.pdf_s3_key)
        except Exception:
            pass

    return CockCertificationResponse(
        id=certification.id,
        status=certification.status.value,
        length_inches=certification.length_inches,
        girth_inches=certification.girth_inches,
        size_category=certification.size_category.value if certification.size_category else None,
        pleasure_zone=certification.pleasure_zone.name if certification.pleasure_zone else None,
        pleasure_zone_label=certification.pleasure_zone_label,
        description=certification.description,
        confidence=certification.confidence,
        reference_objects_used=certification.reference_objects_used,
        pdf_url=pdf_url,
        certified_at=certification.certified_at,
    )


@router.get("/{cert_id}/pdf")
def download_pdf(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get presigned URL for PDF download."""
    certification = (
        db.query(CockCertification)
        .filter(
            CockCertification.id == cert_id,
            CockCertification.user_id == user.id,
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


@router.get("/history/all", response_model=list[CockHistoryItem])
def get_history(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get user's cock certification history."""
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
    return [
        CockHistoryItem(
            id=c.id,
            length_inches=c.length_inches,
            girth_inches=c.girth_inches,
            size_category=c.size_category.value if c.size_category else None,
            pleasure_zone=c.pleasure_zone.name if c.pleasure_zone else None,
            pleasure_zone_label=c.pleasure_zone_label,
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
        db.query(CockCertification)
        .filter(
            CockCertification.id == cert_id,
            CockCertification.status == CockCertificationStatus.completed,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    return {
        "length_inches": certification.length_inches,
        "girth_inches": certification.girth_inches,
        "size_category": certification.size_category.value if certification.size_category else None,
        "pleasure_zone": certification.pleasure_zone.name if certification.pleasure_zone else None,
        "pleasure_zone_label": certification.pleasure_zone_label,
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
        db.query(CockCertification)
        .filter(
            CockCertification.id == cert_id,
            CockCertification.user_id == user.id,
        )
        .first()
    )

    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    # Delete image from S3
    s3 = S3Service()
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

    return {"success": True}
