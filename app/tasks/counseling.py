"""Celery task for counseling chat responses."""

import logging

from app.celery_worker import celery_app
from app.db import get_db_context
from app.llm import execute_text_task_plain
from app.llm.prompts import build_counseling_prompt
from app.models import Analysis, CounselingMessage, CounselingSession
from app.models.counseling import MessageStatus

logger = logging.getLogger(__name__)


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

        # Get user's analysis history for context
        user_analyses = (
            db.query(Analysis)
            .filter(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .limit(10)
            .all()
        )

        # Build system prompt with analysis history
        system_prompt = build_counseling_prompt(user_analyses)

        try:
            # Execute LLM task
            assistant_content = execute_text_task_plain(
                messages=messages,
                system_prompt=system_prompt,
            )

            # Update the message
            assistant_msg.content = assistant_content
            assistant_msg.status = MessageStatus.completed

            # Auto-generate title from first user message if not set
            if not session.title:
                first_user_msg = next(
                    (m for m in session.messages if m.role.value == "user" and m.content),
                    None,
                )
                if first_user_msg:
                    words = first_user_msg.content.split()[:5]
                    session.title = " ".join(words) + ("..." if len(words) == 5 else "")

            db.commit()
            logger.info(f"[{task_id}] Response generated successfully")

            return {"success": True}

        except Exception as e:
            logger.error(f"[{task_id}] Counseling response failed: {e}", exc_info=True)
            assistant_msg.status = MessageStatus.failed
            assistant_msg.content = f"Error: {str(e)}"
            db.commit()
            return {"success": False, "error": str(e)}
