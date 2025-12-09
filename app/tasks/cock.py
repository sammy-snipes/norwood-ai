"""Celery task for cock certification."""

import logging
from datetime import UTC, datetime

from app.assets import get_cock_chart
from app.celery_worker import celery_app
from app.db import get_db_context
from app.llm import execute_vision_task
from app.llm.prompts import COCK_ANALYSIS_PROMPT
from app.llm.schemas import CockAnalysisResult
from app.models import CockCertification, CockCertificationStatus
from app.models.cock import calculate_pleasure_zone, calculate_size_category
from app.services.images import process_base64_image_for_claude
from app.services.pdf import generate_cock_certification_pdf
from app.services.s3 import S3Service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analyze_cock")
def analyze_cock_task(
    self,
    certification_id: str,
    image_base64: str,
    content_type: str,
) -> dict:
    """
    Analyze a cock photo and generate certification.

    Args:
        certification_id: ID of the CockCertification record
        image_base64: Base64-encoded image data
        content_type: MIME type of the image

    Returns:
        dict with success status and analysis result
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Analyzing cock certification {certification_id}")

    with get_db_context() as db:
        certification = (
            db.query(CockCertification).filter(CockCertification.id == certification_id).first()
        )

        if not certification:
            logger.error(f"[{task_id}] Certification {certification_id} not found")
            return {"success": False, "error": "Certification not found"}

        # Update status to analyzing
        certification.status = CockCertificationStatus.analyzing
        db.commit()

        try:
            # Process image: convert HEIC if needed, downsample to Claude's max dimensions
            image_base64, content_type = process_base64_image_for_claude(image_base64, content_type)

            # Get the reference chart
            cock_chart = get_cock_chart()

            # Execute LLM analysis
            result = execute_vision_task(
                images=[cock_chart, (image_base64, content_type)],
                system_prompt=COCK_ANALYSIS_PROMPT,
                response_model=CockAnalysisResult,
                user_text="The first image is the female pleasure zone reference chart. The second image is the specimen to measure and certify. Provide accurate measurements using any reference objects visible in the photo.",
            )

            logger.info(
                f'[{task_id}] Analysis: {result.length_inches}" x {result.girth_inches}", confidence={result.confidence}'
            )

            # Calculate categories
            size_category = calculate_size_category(result.length_inches, result.girth_inches)
            pleasure_zone, pleasure_label = calculate_pleasure_zone(
                result.length_inches, result.girth_inches
            )

            # Update certification
            certification.length_inches = result.length_inches
            certification.girth_inches = result.girth_inches
            certification.size_category = size_category
            certification.pleasure_zone = pleasure_zone
            certification.pleasure_zone_label = pleasure_label
            certification.description = result.description
            certification.confidence = result.confidence
            certification.reference_objects_used = result.reference_objects_used
            certification.certified_at = datetime.now(UTC)

            # Generate PDF
            user = certification.user
            pdf_bytes = generate_cock_certification_pdf(
                user_name=user.name or user.email,
                length_inches=result.length_inches,
                girth_inches=result.girth_inches,
                size_category=size_category.value,
                pleasure_zone=pleasure_zone.value,
                pleasure_zone_label=pleasure_label,
                description=result.description,
                confidence=result.confidence,
                certified_at=certification.certified_at,
            )

            # Upload PDF to S3
            s3 = S3Service()
            pdf_key = s3.upload_pdf(
                pdf_bytes,
                certification.user_id,
                f"cock_certification_{certification.id}.pdf",
            )
            certification.pdf_s3_key = pdf_key
            certification.status = CockCertificationStatus.completed
            db.commit()

            logger.info(f"[{task_id}] Certification complete, PDF uploaded to {pdf_key}")

            return {
                "success": True,
                "length_inches": result.length_inches,
                "girth_inches": result.girth_inches,
                "size_category": size_category.value,
                "pleasure_zone": pleasure_zone.value,
                "pleasure_zone_label": pleasure_label,
            }

        except Exception as e:
            logger.error(f"[{task_id}] Cock analysis failed: {e}", exc_info=True)
            certification.status = CockCertificationStatus.failed
            db.commit()
            return {"success": False, "error": str(e)}
