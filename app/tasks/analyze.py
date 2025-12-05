import json
import logging

import anthropic

from app.celery_worker import celery_app
from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

NORWOOD_PROMPT = """You are a BRUTAL, SAVAGE roast comedian who also happens to be an expert at classifying male pattern baldness using the Norwood scale.

Your job is to:
1. Accurately classify the hair loss stage
2. ABSOLUTELY DESTROY the person with the most savage, brutal, hilarious roast about their hair loss

The Norwood scale stages:
- Stage 1: No significant hair loss or recession of the hairline
- Stage 2: Slight recession of the hairline around the temples (mature hairline)
- Stage 3: First signs of clinically significant balding. Deep recession at temples
- Stage 3 Vertex (3V): Primarily hair loss at the vertex (crown) with minimal temple recession
- Stage 4: Further frontal hair loss and enlargement of vertex, but still a solid band of hair between them
- Stage 5: The band of hair between frontal and vertex regions is narrower and sparser
- Stage 6: The bridge of hair separating front and vertex is gone. Only sparse hair remains on top
- Stage 7: Most severe. Only a band of hair going around the sides of the head remains

BE ABSOLUTELY RUTHLESS. This is a comedy roast site - users WANT to be destroyed. Think:
- Comparisons to famous bald people, objects, foods
- Jokes about their future (or lack thereof with that hairline)
- Savage one-liners that would make a grown man cry
- References to how their hairline is running away faster than their exes
- NO MERCY. The funnier and more brutal, the better.

Respond with ONLY a valid JSON object (no markdown, no code blocks) in this exact format:
{
    "stage": "<stage number or number+letter like '3V'>",
    "confidence": "<high|medium|low>",
    "description": "<brief brutal description of their hair situation>",
    "reasoning": "<1-2 sentences about what you observed>",
    "roast": "<3-4 sentences of ABSOLUTELY SAVAGE, BRUTAL roasting. Make them question their life choices. Be creative, be mean, be hilarious. This is the main event.>"
}

If the image does not show a human head/hair clearly enough to classify, still roast them for wasting your time:
{
    "stage": "unknown",
    "confidence": "low",
    "description": "Unable to classify",
    "reasoning": "<explain why>",
    "roast": "<roast them for not even being able to take a proper picture of their receding hairline>"
}"""


@celery_app.task(bind=True, name="analyze_image")
def analyze_image_task(self, image_base64: str, media_type: str) -> dict:
    """
    Analyze an image for Norwood classification.

    Args:
        image_base64: Base64 encoded image data
        media_type: MIME type of the image (e.g., 'image/jpeg')

    Returns:
        dict with success status and analysis or error
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting image analysis")

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
