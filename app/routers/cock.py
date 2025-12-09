"""Cock certification router - premium only."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.routers.auth import decode_token
from app.services import cock as cock_service
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
    certification = cock_service.create_certification(user, db)

    # Queue analysis task (processes image, uploads to S3, analyzes)
    task = analyze_cock_task.delay(
        certification.id,
        request.image_base64,
        request.content_type,
    )

    return SubmitPhotoResponse(certification_id=certification.id, task_id=task.id)


@router.get("/{cert_id}", response_model=CockCertificationResponse)
def get_certification(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get certification status and results."""
    certification = cock_service.get_by_id(cert_id, user, db)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    status_data = cock_service.get_status(certification)
    return CockCertificationResponse(**status_data)


@router.get("/{cert_id}/pdf")
def download_pdf(
    cert_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get presigned URL for PDF download."""
    certification = cock_service.get_by_id(cert_id, user, db)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found")

    pdf_url = cock_service.get_pdf_url(certification)
    if not pdf_url:
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    return {"pdf_url": pdf_url}


@router.get("/history/all", response_model=list[CockHistoryItem])
def get_history(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get user's cock certification history."""
    history = cock_service.get_history(user, db)
    return [CockHistoryItem(**item) for item in history]


@router.get("/public/{cert_id}")
def get_public_certification(
    cert_id: str,
    db: Session = Depends(get_db),
):
    """Get public certification info (no auth required)."""
    info = cock_service.get_public_info(cert_id, db)
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
    deleted = cock_service.delete_with_cleanup(cert_id, user, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Certification not found")
    return {"success": True}
