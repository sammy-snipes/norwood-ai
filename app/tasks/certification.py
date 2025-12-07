"""Celery tasks for Norwood certification."""

import logging
from datetime import UTC, datetime

from app.assets import get_norwood_chart
from app.celery_worker import celery_app
from app.db import get_db_context
from app.llm import execute_vision_task
from app.llm.prompts import CERTIFICATION_DIAGNOSIS_PROMPT, PHOTO_VALIDATION_PROMPT
from app.llm.schemas import CertificationDiagnosis, PhotoValidationResult
from app.models import (
    Certification,
    CertificationPhoto,
    CertificationStatus,
    PhotoType,
    ValidationStatus,
)
from app.services.pdf import generate_certification_pdf
from app.services.s3 import S3Service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="validate_certification_photo")
def validate_certification_photo_task(
    self,
    photo_id: str,
    image_base64: str,
    content_type: str,
    photo_type: str,
) -> dict:
    """
    Validate a certification photo for quality.

    Args:
        photo_id: ID of the CertificationPhoto record
        image_base64: Base64-encoded image data
        content_type: MIME type of the image
        photo_type: Type of photo (front, left, right)

    Returns:
        dict with success status and validation result
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Validating {photo_type} photo {photo_id}")

    try:
        # Execute LLM validation
        result = execute_vision_task(
            images=[(image_base64, content_type)],
            system_prompt=PHOTO_VALIDATION_PROMPT,
            response_model=PhotoValidationResult,
            user_text=f"Validate this {photo_type.upper()} photo for Norwood certification.",
        )

        logger.info(f"[{task_id}] Validation result: approved={result.approved}")

        # Update photo record
        with get_db_context() as db:
            photo = db.query(CertificationPhoto).filter(CertificationPhoto.id == photo_id).first()

            if not photo:
                logger.error(f"[{task_id}] Photo {photo_id} not found")
                return {"success": False, "error": "Photo not found"}

            photo.validation_status = (
                ValidationStatus.approved if result.approved else ValidationStatus.rejected
            )
            photo.rejection_reason = result.rejection_reason
            photo.quality_notes = result.quality_notes
            db.commit()

        return {
            "success": True,
            "approved": result.approved,
            "rejection_reason": result.rejection_reason,
            "quality_notes": result.quality_notes,
        }

    except Exception as e:
        logger.error(f"[{task_id}] Photo validation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(bind=True, name="generate_certification_diagnosis")
def generate_certification_diagnosis_task(self, certification_id: str) -> dict:
    """
    Generate final certification diagnosis from 3 validated photos.

    Args:
        certification_id: ID of the Certification record

    Returns:
        dict with success status and diagnosis result
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Generating diagnosis for certification {certification_id}")

    with get_db_context() as db:
        certification = db.query(Certification).filter(Certification.id == certification_id).first()

        if not certification:
            logger.error(f"[{task_id}] Certification {certification_id} not found")
            return {"success": False, "error": "Certification not found"}

        # Update status to analyzing
        certification.status = CertificationStatus.analyzing
        db.commit()

        try:
            # Get all approved photos
            photos = {
                p.photo_type: p
                for p in certification.photos
                if p.validation_status == ValidationStatus.approved
            }

            required = {PhotoType.front, PhotoType.left, PhotoType.right}
            if set(photos.keys()) != required:
                missing = required - set(photos.keys())
                logger.error(f"[{task_id}] Missing photos: {missing}")
                certification.status = CertificationStatus.failed
                db.commit()
                return {"success": False, "error": f"Missing approved photos: {missing}"}

            # Fetch images from S3
            s3 = S3Service()
            images = [get_norwood_chart()]  # Start with reference chart
            for photo_type in [PhotoType.front, PhotoType.left, PhotoType.right]:
                photo = photos[photo_type]
                image_data, img_content_type = s3.get_image_base64(photo.s3_key)
                images.append((image_data, img_content_type))
                logger.info(f"[{task_id}] Fetched {photo_type.value} image from S3")

            # Generate diagnosis
            result = execute_vision_task(
                images=images,
                system_prompt=CERTIFICATION_DIAGNOSIS_PROMPT,
                response_model=CertificationDiagnosis,
                user_text="The first image is the Norwood scale reference chart. The following images are the user's photos in order: FRONT, LEFT, RIGHT. Provide the official Norwood certification diagnosis.",
            )

            logger.info(
                f"[{task_id}] Diagnosis: Stage {result.norwood_stage}{result.norwood_variant or ''}"
            )

            # Update certification with diagnosis
            certification.norwood_stage = result.norwood_stage
            certification.norwood_variant = result.norwood_variant
            certification.confidence = result.confidence
            certification.clinical_assessment = result.clinical_assessment
            certification.observable_features = result.observable_features
            certification.differential_considerations = result.differential_considerations
            certification.certified_at = datetime.now(UTC)

            # Generate PDF
            user = certification.user
            pdf_bytes = generate_certification_pdf(
                user_name=user.name or user.email,
                norwood_stage=result.norwood_stage,
                norwood_variant=result.norwood_variant,
                confidence=result.confidence,
                clinical_assessment=result.clinical_assessment,
                certified_at=certification.certified_at,
            )

            # Upload PDF to S3
            pdf_key = s3.upload_pdf(
                pdf_bytes,
                certification.user_id,
                f"certification_{certification.id}.pdf",
            )
            certification.pdf_s3_key = pdf_key
            certification.status = CertificationStatus.completed
            db.commit()

            logger.info(f"[{task_id}] Certification complete, PDF uploaded to {pdf_key}")

            return {
                "success": True,
                "norwood_stage": result.norwood_stage,
                "norwood_variant": result.norwood_variant,
                "confidence": result.confidence,
            }

        except Exception as e:
            logger.error(f"[{task_id}] Certification diagnosis failed: {e}", exc_info=True)
            certification.status = CertificationStatus.failed
            db.commit()
            return {"success": False, "error": str(e)}
