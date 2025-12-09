"""Analysis service for managing Norwood analyses."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Analysis, User
from app.services.s3 import S3Service

logger = logging.getLogger(__name__)
settings = get_settings()

# Allowed image types for analysis
ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/heic",
    "image/heif",
]


def check_can_analyze(user: User) -> bool:
    """Check if user has remaining analyses."""
    return user.is_admin or user.is_premium or user.free_analyses_remaining > 0


def consume_analysis_quota(user: User, db: Session) -> None:
    """Decrement free analysis count for non-premium users."""
    if not user.is_admin and not user.is_premium:
        user.free_analyses_remaining -= 1
        db.commit()
        logger.info(f"User {user.id} has {user.free_analyses_remaining} free analyses remaining")


def validate_image_type(content_type: str) -> bool:
    """Check if image type is allowed."""
    return content_type in ALLOWED_IMAGE_TYPES


def validate_image_size(size_bytes: int) -> bool:
    """Check if image size is within limits."""
    return size_bytes <= settings.max_image_size_bytes


def get_history_with_urls(user: User, db: Session, limit: int = 50) -> list[dict]:
    """Get user's analysis history with presigned S3 URLs."""
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .all()
    )

    s3 = S3Service() if settings.S3_BUCKET_NAME else None
    result = []

    for analysis in analyses:
        item = {
            "id": analysis.id,
            "norwood_stage": analysis.norwood_stage,
            "confidence": analysis.confidence,
            "title": analysis.title,
            "analysis_text": analysis.analysis_text,
            "reasoning": analysis.reasoning,
            "created_at": analysis.created_at,
            "image_url": None,
        }

        if analysis.image_url and s3:
            try:
                item["image_url"] = s3.get_presigned_url(analysis.image_url)
            except Exception:
                pass

        result.append(item)

    return result


def delete_with_cleanup(analysis_id: str, user: User, db: Session) -> bool:
    """Delete an analysis and its S3 image."""
    analysis = (
        db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    )

    if not analysis:
        return False

    # Delete image from S3 if exists
    if analysis.image_url and settings.S3_BUCKET_NAME:
        try:
            s3 = S3Service()
            s3.delete_image(analysis.image_url)
            logger.info(f"Deleted S3 image: {analysis.image_url}")
        except Exception as e:
            logger.warning(f"Failed to delete S3 image: {e}")

    db.delete(analysis)
    db.commit()
    logger.info(f"Deleted analysis {analysis_id}")

    return True
