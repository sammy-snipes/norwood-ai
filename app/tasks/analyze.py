"""Celery task for Norwood image analysis."""

import logging

from app.assets import get_norwood_chart
from app.celery_worker import celery_app
from app.config import get_settings
from app.db import get_db_context
from app.llm import execute_vision_task
from app.llm.prompts import NORWOOD_ANALYSIS_PROMPT
from app.llm.schemas import NorwoodAnalysisResult
from app.models import Analysis, User
from app.services.images import process_and_upload_image

settings = get_settings()
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analyze_image")
def analyze_image_task(self, image_base64: str, media_type: str, user_id: str) -> dict:
    """
    Analyze an image for Norwood classification.

    Args:
        image_base64: Base64 encoded image data
        media_type: MIME type of the image (e.g., 'image/jpeg')
        user_id: ID of the user requesting the analysis

    Returns:
        dict with success status and analysis or error
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting analysis for user {user_id}")

    try:
        # Process image and upload to S3
        image_key, image_base64, media_type = process_and_upload_image(
            image_base64, media_type, user_id, "analyses"
        )

        # Execute LLM task with structured output
        norwood_chart = get_norwood_chart()
        result = execute_vision_task(
            images=[norwood_chart, (image_base64, media_type)],
            system_prompt=NORWOOD_ANALYSIS_PROMPT,
            response_model=NorwoodAnalysisResult,
            user_text="The first image is the Norwood scale reference chart. The second image is the user's photo to analyze. Classify their Norwood stage.",
        )

        logger.info(f"[{task_id}] LLM returned stage {result.norwood_stage}")

        # Save analysis to database
        with get_db_context() as db:
            db_analysis = Analysis(
                user_id=user_id,
                norwood_stage=result.norwood_stage,
                confidence=result.confidence,
                title=result.title,
                analysis_text=result.analysis_text,
                reasoning=result.reasoning,
                image_url=image_key,
            )
            db.add(db_analysis)

            # Decrement free analyses if user is not admin/premium
            user = db.query(User).filter(User.id == user_id).first()
            if user and not user.is_admin and not user.is_premium:
                if user.free_analyses_remaining > 0:
                    user.free_analyses_remaining -= 1

            db.commit()
            logger.info(f"[{task_id}] Analysis saved, stage: {result.norwood_stage}")

        return {
            "success": True,
            "analysis": {
                "stage": str(result.norwood_stage),
                "confidence": result.confidence,
                "title": result.title,
                "description": result.description,
                "analysis_text": result.analysis_text,
                "reasoning": result.reasoning,
            },
        }

    except Exception as e:
        logger.error(f"[{task_id}] Analysis failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
