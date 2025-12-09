"""Celery task for Twitter hairline analysis."""

import logging

from app.assets import get_norwood_chart
from app.celery_worker import celery_app
from app.llm import execute_vision_task
from app.llm.schemas import TwitterAnalysisResult
from app.twitter.prompt import TWITTER_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analyze_twitter_image")
def analyze_twitter_image_task(self, image_base64: str, media_type: str) -> dict:
    """
    Analyze an image for Twitter and generate a reply.

    Args:
        image_base64: Base64 encoded image data
        media_type: MIME type of the image (e.g., 'image/jpeg')

    Returns:
        dict with success status and reply text or error
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting Twitter analysis")

    try:
        norwood_chart = get_norwood_chart()
        result = execute_vision_task(
            images=[norwood_chart, (image_base64, media_type)],
            system_prompt=TWITTER_ANALYSIS_PROMPT,
            response_model=TwitterAnalysisResult,
            user_text="The first image is the Norwood scale reference. The second is the photo to analyze. Give your assessment.",
        )

        logger.info(f"[{task_id}] Analysis complete: Norwood {result.norwood_stage}")

        return {
            "success": True,
            "norwood_stage": result.norwood_stage,
            "reply_text": result.reply_text,
        }

    except Exception as e:
        logger.error(f"[{task_id}] Analysis failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
