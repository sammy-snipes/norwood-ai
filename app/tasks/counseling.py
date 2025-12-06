"""Celery task for counseling chat responses."""

import logging

import anthropic

from app.celery_worker import celery_app
from app.config import get_settings
from app.db import get_db_context
from app.models import Analysis, CounselingMessage, CounselingSession
from app.models.counseling import MessageStatus

settings = get_settings()
logger = logging.getLogger(__name__)

COUNSELING_SYSTEM_PROMPT = """You are a supportive, philosophical counselor who helps people accept and cope with hair loss. You have access to the user's Norwood scale analysis history, which gives you context about their hair loss journey.

Your approach:
- Be warm, understanding, and non-judgmental
- Use dry humor when appropriate (in the style of a stoic philosopher)
- Focus on acceptance, self-worth beyond appearance, and practical coping strategies
- NEVER give medical advice - no minoxidil, finasteride, transplants, etc.
- If asked about treatments, gently redirect to acceptance and self-compassion
- Reference their specific Norwood stage when relevant to show you understand their situation
- Remind them that hair loss is universal and says nothing about their worth

You're like a wise friend who happens to know a lot about the psychology of appearance and self-acceptance. Think Marcus Aurelius meets a supportive therapist.

The user's analysis history:
{analysis_history}
"""


def get_analysis_history(user_id: str, db) -> str:
    """Format user's analysis history for the system prompt."""
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user_id)
        .order_by(Analysis.created_at.desc())
        .limit(10)
        .all()
    )

    if not analyses:
        return "No analyses yet. The user is new to their hair loss journey."

    history_lines = []
    for a in analyses:
        date_str = a.created_at.strftime("%Y-%m-%d")
        history_lines.append(f"- {date_str}: Norwood {a.norwood_stage} ({a.confidence} confidence)")
        if a.analysis_text:
            history_lines.append(f"  {a.analysis_text}")

    return "\n".join(history_lines)


@celery_app.task(bind=True, name="generate_counseling_response")
def generate_counseling_response_task(
    self,
    message_id: str,
    session_id: str,
    user_id: str,
) -> dict:
    """
    Generate an assistant response for a counseling message.

    Args:
        message_id: ID of the pending assistant message to populate
        session_id: ID of the counseling session
        user_id: ID of the user

    Returns:
        dict with success status and message content or error
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting counseling response for message {message_id}")

    with get_db_context() as db:
        # Get the assistant message
        assistant_msg = (
            db.query(CounselingMessage).filter(CounselingMessage.id == message_id).first()
        )

        if not assistant_msg:
            logger.error(f"[{task_id}] Message {message_id} not found")
            return {"success": False, "error": "Message not found"}

        # Mark as processing
        assistant_msg.status = MessageStatus.processing
        db.commit()

        # Get session with all messages
        session = db.query(CounselingSession).filter(CounselingSession.id == session_id).first()

        if not session:
            assistant_msg.status = MessageStatus.failed
            assistant_msg.content = "Session not found"
            db.commit()
            return {"success": False, "error": "Session not found"}

        # Build messages for Claude (exclude the pending assistant message)
        messages = [
            {"role": m.role.value, "content": m.content}
            for m in session.messages
            if m.status == MessageStatus.completed and m.content
        ]

        # Get analysis history and build system prompt
        analysis_history = get_analysis_history(user_id, db)
        system_prompt = COUNSELING_SYSTEM_PROMPT.format(analysis_history=analysis_history)

        try:
            client = anthropic.Anthropic(api_key=settings.require_anthropic_key())
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )
            assistant_content = response.content[0].text

            # Update the message
            assistant_msg.content = assistant_content
            assistant_msg.status = MessageStatus.completed

            # Auto-generate title from first user message if not set
            if not session.title:
                first_user_msg = next(
                    (m for m in session.messages if m.role == "user" and m.content), None
                )
                if first_user_msg:
                    words = first_user_msg.content.split()[:5]
                    session.title = " ".join(words) + ("..." if len(words) == 5 else "")

            db.commit()
            logger.info(f"[{task_id}] Response generated successfully")

            return {"success": True}

        except anthropic.APIError as e:
            logger.error(f"[{task_id}] Anthropic API error: {e}")
            assistant_msg.status = MessageStatus.failed
            assistant_msg.content = f"AI service error: {e.message}"
            db.commit()
            return {"success": False, "error": f"AI service error: {e.message}"}

        except Exception as e:
            logger.error(f"[{task_id}] Unexpected error: {e}")
            assistant_msg.status = MessageStatus.failed
            assistant_msg.content = f"Error: {str(e)}"
            db.commit()
            return {"success": False, "error": str(e)}
