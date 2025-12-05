import json
import logging

import anthropic

from app.celery_worker import celery_app
from app.config import get_settings
from app.db import get_db_context
from app.models import Analysis, User

settings = get_settings()

logger = logging.getLogger(__name__)


def parse_stage_to_int(stage: str) -> int:
    """Convert stage string to integer (e.g., '3V' -> 3, '5' -> 5)."""
    stage_str = str(stage).upper().replace("V", "").replace("A", "").strip()
    try:
        return int(stage_str)
    except ValueError:
        return 0  # unknown

NORWOOD_PROMPT = """You are a dry, philosophical observer of human vanity and the inevitability of time. You classify male pattern baldness using the Norwood scale, but more importantly, you reflect on what it means.

Your job is to:
1. Accurately classify the hair loss stage
2. Provide a contemplative, darkly humorous reflection on mortality, vanity, and the human condition as it relates to their hair situation

The Norwood scale stages:
- Stage 1: No significant hair loss or recession of the hairline
- Stage 2: Slight recession of the hairline around the temples (mature hairline)
- Stage 3: First signs of clinically significant balding. Deep recession at temples
- Stage 3 Vertex (3V): Primarily hair loss at the vertex (crown) with minimal temple recession
- Stage 4: Further frontal hair loss and enlargement of vertex, but still a solid band of hair between them
- Stage 5: The band of hair between frontal and vertex regions is narrower and sparser
- Stage 6: The bridge of hair separating front and vertex is gone. Only sparse hair remains on top
- Stage 7: Most severe. Only a band of hair going around the sides of the head remains

Your tone should be:
- Dry, understated, philosophical
- Darkly funny but not mean-spirited
- Reflective on time, genetics, acceptance
- Like a stoic philosopher who also happens to notice hairlines
- Think Marcus Aurelius meets a dermatologist

Respond with ONLY a valid JSON object (no markdown, no code blocks) in this exact format:
{
    "stage": "<stage number or number+letter like '3V'>",
    "confidence": "<high|medium|low>",
    "description": "<brief, matter-of-fact description of their hair situation>",
    "reasoning": "<1-2 sentences about what you observed>",
    "title": "<punchy 3-5 word title, like a headline or epitaph>",
    "analysis_text": "<2-3 sentences of dry, philosophical reflection. Contemplate time, vanity, acceptance. Be wry, not cruel. Make them think while they laugh.>"
}

If the image does not show a human head/hair clearly enough to classify:
{
    "stage": "unknown",
    "confidence": "low",
    "description": "Unable to classify",
    "reasoning": "<explain why>",
    "title": "The Unseen",
    "analysis_text": "<philosophical musing on the nature of seeing and being seen, or the futility of trying to capture oneself in an image>"
}"""


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
    logger.info(f"[{task_id}] Starting image analysis for user {user_id}")

    try:
        api_key = settings.require_anthropic_key()
        client = anthropic.Anthropic(api_key=api_key)

        logger.info(f"[{task_id}] Calling Claude API...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": NORWOOD_PROMPT,
                        },
                    ],
                }
            ],
        )

        logger.info(f"[{task_id}] Claude API call completed")
        response_text = message.content[0].text
        logger.info(f"[{task_id}] Response: {response_text}")

        try:
            analysis = json.loads(response_text)

            # Save analysis to database
            with get_db_context() as db:
                # Create analysis record
                stage_int = parse_stage_to_int(analysis.get("stage", "0"))
                db_analysis = Analysis(
                    user_id=user_id,
                    norwood_stage=stage_int,
                    confidence=analysis.get("confidence", "low"),
                    title=analysis.get("title", "Untitled"),
                    analysis_text=analysis.get("analysis_text", ""),
                    reasoning=analysis.get("reasoning"),
                    image_url=None,  # Will be S3 URL in future
                )
                db.add(db_analysis)

                # Decrement free analyses if user is not admin/premium
                user = db.query(User).filter(User.id == user_id).first()
                if user and not user.is_admin and not user.is_premium:
                    if user.free_analyses_remaining > 0:
                        user.free_analyses_remaining -= 1
                        logger.info(f"[{task_id}] Decremented free analyses for user {user_id}, remaining: {user.free_analyses_remaining}")

                db.commit()
                logger.info(f"[{task_id}] Saved analysis {db_analysis.id} to database")

            return {"success": True, "analysis": analysis}
        except json.JSONDecodeError as e:
            logger.error(f"[{task_id}] Failed to parse response: {e}")
            return {"success": False, "error": "Failed to parse analysis response"}

    except anthropic.APIError as e:
        logger.error(f"[{task_id}] Anthropic API error: {e}")
        return {"success": False, "error": f"AI service error: {e.message}"}
    except Exception as e:
        logger.error(f"[{task_id}] Unexpected error: {e}")
        return {"success": False, "error": str(e)}
