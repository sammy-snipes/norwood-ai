"""Celery tasks for forum AI agent responses."""

import logging
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.sql.expression import func

from app.celery_worker import celery_app
from app.db import get_db_context
from app.llm import execute_text_task_plain
from app.models import ForumAgentSchedule, ForumPersona, ForumReply, ForumReplyStatus, ForumThread

logger = logging.getLogger(__name__)


def calculate_next_delay_minutes(reply_count: int) -> int:
    """
    Calculate delay in minutes based on exponential backoff.

    Schedule:
    - Reply 1: 2 minutes
    - Reply 2: 5 minutes
    - Reply 3: 15 minutes
    - Reply 4: 30 minutes
    - Reply 5: 1 hour
    - Reply 6: 2 hours
    - Reply 7: 4 hours
    - Reply 8: 8 hours
    - Reply 9+: 24 hours (daily)
    """
    delays = [2, 5, 15, 30, 60, 120, 240, 480, 1440]
    if reply_count >= len(delays):
        return delays[-1]  # 24 hours
    return delays[reply_count]


def build_persona_prompt(
    persona: ForumPersona,
    thread_title: str,
    thread_content: str,
    recent_replies: list[dict],
) -> str:
    """
    Build the full prompt for a persona reply.

    Args:
        persona: The persona to use
        thread_title: The thread's title
        thread_content: The original post content
        recent_replies: List of recent replies with keys: author_name, content

    Returns:
        System prompt string for the LLM
    """
    # Build conversation context
    context = f"""THREAD TITLE: {thread_title}

ORIGINAL POST:
{thread_content}

"""
    if recent_replies:
        context += "RECENT DISCUSSION:\n"
        for reply in recent_replies[-10:]:  # Last 10 replies for context
            author = reply.get("author_name", "Anonymous")
            context += f"\n{author}: {reply['content']}\n"

    return f"""{persona.system_prompt}

---

{context}

Write a reply to this discussion. Be yourself and add to the conversation naturally. Don't repeat what others have said. Keep it concise."""


def get_reply_author_name(reply: ForumReply) -> str:
    """Get the display name for a reply's author."""
    if reply.persona:
        return reply.persona.name
    if reply.user:
        return reply.user.name or "Anonymous"
    return "Anonymous"


@celery_app.task(bind=True, name="initialize_forum_agent_schedules")
def initialize_forum_agent_schedules_task(self, thread_id: str) -> dict:
    """
    Initialize agent schedules when a new thread is created.

    Randomly selects 3-5 personas to participate in the thread.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Initializing agent schedules for thread {thread_id}")

    with get_db_context() as db:
        thread = db.query(ForumThread).filter(ForumThread.id == thread_id).first()
        if not thread:
            logger.error(f"[{task_id}] Thread {thread_id} not found")
            return {"success": False, "error": "Thread not found"}

        # Get all active personas
        personas = (
            db.query(ForumPersona)
            .filter(ForumPersona.is_active.is_(True))
            .all()
        )

        if not personas:
            logger.warning(f"[{task_id}] No active personas found")
            return {"success": False, "error": "No active personas"}

        # Randomly select 3-5 personas to participate (or all if fewer)
        num_participants = min(random.randint(3, 5), len(personas))
        selected_personas = random.sample(personas, num_participants)

        now = datetime.now(UTC)

        # Create schedules with staggered initial delays
        for i, persona in enumerate(selected_personas):
            # Stagger: first at 2 min, then every 1-2 minutes after
            delay_minutes = 2 + i + random.random()
            next_reply_at = now + timedelta(minutes=delay_minutes)

            schedule = ForumAgentSchedule(
                thread_id=thread_id,
                persona_id=persona.id,
                next_reply_at=next_reply_at,
                reply_count=0,
                is_active=True,
            )
            db.add(schedule)

            logger.info(
                f"[{task_id}] Created schedule for {persona.name} "
                f"on thread {thread_id}, first reply at {next_reply_at}"
            )

        db.commit()

    return {"success": True, "thread_id": thread_id, "participants": num_participants}


@celery_app.task(bind=True, name="generate_forum_agent_reply")
def generate_forum_agent_reply_task(
    self,
    schedule_id: str,
    thread_id: str,
    persona_id: str,
) -> dict:
    """
    Generate an AI agent reply for a forum thread.

    Args:
        schedule_id: ID of the agent schedule
        thread_id: ID of the thread to reply to
        persona_id: ID of the persona to use
    """
    task_id = self.request.id

    with get_db_context() as db:
        # Get the schedule and verify it's still valid
        schedule = (
            db.query(ForumAgentSchedule)
            .filter(ForumAgentSchedule.id == schedule_id)
            .with_for_update()  # Lock the row to prevent race conditions
            .first()
        )

        if not schedule:
            logger.warning(f"[{task_id}] Schedule {schedule_id} not found")
            return {"success": False, "error": "Schedule not found"}

        if not schedule.is_active:
            logger.info(f"[{task_id}] Schedule {schedule_id} is no longer active")
            return {"success": False, "error": "Schedule inactive"}

        # Get the persona
        persona = db.query(ForumPersona).filter(ForumPersona.id == persona_id).first()
        if not persona:
            logger.error(f"[{task_id}] Persona {persona_id} not found")
            schedule.is_active = False
            db.commit()
            return {"success": False, "error": "Persona not found"}

        logger.info(f"[{task_id}] Generating {persona.name} reply for thread {thread_id}")

        # Get the thread
        thread = db.query(ForumThread).filter(ForumThread.id == thread_id).first()
        if not thread:
            logger.error(f"[{task_id}] Thread {thread_id} not found")
            schedule.is_active = False
            db.commit()
            return {"success": False, "error": "Thread not found"}

        # Create pending reply
        reply = ForumReply(
            thread_id=thread_id,
            user_id=None,  # Agent replies have no user
            persona_id=persona.id,
            status=ForumReplyStatus.pending,
            content=None,
        )
        db.add(reply)
        db.commit()
        db.refresh(reply)

        reply_id = reply.id
        logger.info(f"[{task_id}] Created pending reply {reply_id}")

        # Update reply status to processing
        reply.status = ForumReplyStatus.processing
        db.commit()

        # Get recent replies for context
        recent_replies = (
            db.query(ForumReply)
            .filter(
                ForumReply.thread_id == thread_id,
                ForumReply.status == ForumReplyStatus.completed,
                ForumReply.id != reply_id,
            )
            .order_by(ForumReply.created_at.desc())
            .limit(10)
            .all()
        )

        # Build context for LLM
        reply_context = []
        for r in reversed(recent_replies):  # Chronological order
            reply_context.append({
                "author_name": get_reply_author_name(r),
                "content": r.content,
            })

        # Build the prompt
        system_prompt = build_persona_prompt(
            persona=persona,
            thread_title=thread.title,
            thread_content=thread.content,
            recent_replies=reply_context,
        )

        try:
            # Generate response using LLM
            content = execute_text_task_plain(
                messages=[{"role": "user", "content": "Write your reply now."}],
                system_prompt=system_prompt,
            )

            # Update reply with content
            reply.content = content
            reply.status = ForumReplyStatus.completed

            # Update schedule for next reply
            schedule.reply_count += 1
            schedule.last_replied_at = datetime.now(UTC)

            next_delay = calculate_next_delay_minutes(schedule.reply_count)
            schedule.next_reply_at = datetime.now(UTC) + timedelta(minutes=next_delay)

            # Update thread's updated_at
            thread.updated_at = datetime.now(UTC)

            db.commit()

            logger.info(
                f"[{task_id}] {persona.name} reply generated successfully. "
                f"Next reply in {next_delay} minutes"
            )

            return {
                "success": True,
                "reply_id": reply_id,
                "persona_name": persona.name,
                "content": content,
            }

        except Exception as e:
            logger.error(f"[{task_id}] Failed to generate reply: {e}", exc_info=True)
            reply.status = ForumReplyStatus.failed
            reply.content = "Error generating response"
            db.commit()

            return {"success": False, "error": str(e)}


@celery_app.task(name="check_forum_agent_schedules")
def check_forum_agent_schedules_task() -> dict:
    """
    Periodic task to check for due agent schedules and queue replies.

    This runs every minute via Celery Beat to catch any missed schedules.
    """
    logger.debug("Checking forum agent schedules...")

    with get_db_context() as db:
        now = datetime.now(UTC)

        # Find all active schedules that are due (with persona_id set)
        due_schedules = (
            db.query(ForumAgentSchedule)
            .filter(
                ForumAgentSchedule.is_active.is_(True),
                ForumAgentSchedule.next_reply_at <= now,
                ForumAgentSchedule.next_reply_at.isnot(None),
                ForumAgentSchedule.persona_id.isnot(None),
            )
            .all()
        )

        if not due_schedules:
            return {"success": True, "queued": 0}

        queued = 0
        for schedule in due_schedules:
            # Queue the reply generation task
            generate_forum_agent_reply_task.delay(
                schedule_id=schedule.id,
                thread_id=schedule.thread_id,
                persona_id=schedule.persona_id,
            )
            queued += 1

            persona_name = schedule.persona.name if schedule.persona else "Unknown"
            logger.info(
                f"Queued {persona_name} reply for thread {schedule.thread_id}"
            )

            # Clear next_reply_at to prevent duplicate queueing
            # The task will set the next time after completion
            schedule.next_reply_at = None

        db.commit()

        logger.info(f"Queued {queued} agent replies")
        return {"success": True, "queued": queued}


@celery_app.task(bind=True, name="bump_agent_schedules_on_user_reply")
def bump_agent_schedules_on_user_reply_task(self, thread_id: str) -> dict:
    """
    Bump agent schedules to respond soon after a user posts a reply.

    When a user replies to a thread, we want agents to respond within 1-2 minutes
    (staggered) instead of waiting for their normal schedule.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Bumping agent schedules for thread {thread_id} due to user reply")

    with get_db_context() as db:
        # Get all active schedules for this thread
        schedules = (
            db.query(ForumAgentSchedule)
            .filter(
                ForumAgentSchedule.thread_id == thread_id,
                ForumAgentSchedule.is_active.is_(True),
            )
            .all()
        )

        if not schedules:
            logger.info(f"[{task_id}] No active schedules found for thread {thread_id}")
            return {"success": True, "bumped": 0}

        now = datetime.now(UTC)
        bumped = 0

        for i, schedule in enumerate(schedules):
            # Only bump if the current schedule is more than 2 minutes away
            # This prevents constantly resetting if users are actively chatting
            if schedule.next_reply_at is None or schedule.next_reply_at > now + timedelta(minutes=2):
                # Stagger responses: 60-120 seconds apart
                delay_seconds = 60 + (i * 20) + random.randint(0, 10)
                schedule.next_reply_at = now + timedelta(seconds=delay_seconds)
                bumped += 1

                persona_name = schedule.persona.name if schedule.persona else "Unknown"
                logger.info(
                    f"[{task_id}] Bumped {persona_name} schedule to "
                    f"{schedule.next_reply_at} ({delay_seconds}s from now)"
                )

        db.commit()

        logger.info(f"[{task_id}] Bumped {bumped} agent schedules for thread {thread_id}")
        return {"success": True, "bumped": bumped}


@celery_app.task(bind=True, name="generate_direct_agent_reply")
def generate_direct_agent_reply_task(
    self,
    thread_id: str,
    parent_reply_id: str,
    user_reply_content: str,
) -> dict:
    """
    Generate a direct agent reply to a user's message.

    When a user replies to an agent's message, this task generates a nested
    reply from a random persona directly under the user's message.

    Args:
        thread_id: ID of the thread
        parent_reply_id: ID of the user's reply to respond to
        user_reply_content: Content of the user's reply for context
    """
    task_id = self.request.id

    with get_db_context() as db:
        # Pick a random active persona to respond
        persona = (
            db.query(ForumPersona)
            .filter(ForumPersona.is_active.is_(True))
            .order_by(func.random())
            .first()
        )

        if not persona:
            logger.error(f"[{task_id}] No active personas found")
            return {"success": False, "error": "No active personas"}

        logger.info(
            f"[{task_id}] Generating direct {persona.name} reply to user message "
            f"in thread {thread_id}"
        )

        # Get the thread
        thread = db.query(ForumThread).filter(ForumThread.id == thread_id).first()
        if not thread:
            logger.error(f"[{task_id}] Thread {thread_id} not found")
            return {"success": False, "error": "Thread not found"}

        # Verify the parent reply exists
        parent_reply = (
            db.query(ForumReply).filter(ForumReply.id == parent_reply_id).first()
        )
        if not parent_reply:
            logger.error(f"[{task_id}] Parent reply {parent_reply_id} not found")
            return {"success": False, "error": "Parent reply not found"}

        # Create pending reply as a nested reply under the user's message
        reply = ForumReply(
            thread_id=thread_id,
            parent_id=parent_reply_id,  # Nest under the user's reply
            user_id=None,  # Agent replies have no user
            persona_id=persona.id,
            status=ForumReplyStatus.pending,
            content=None,
        )
        db.add(reply)
        db.commit()
        db.refresh(reply)

        reply_id = reply.id
        logger.info(f"[{task_id}] Created pending nested reply {reply_id}")

        # Update reply status to processing
        reply.status = ForumReplyStatus.processing
        db.commit()

        # Get recent replies for context
        recent_replies = (
            db.query(ForumReply)
            .filter(
                ForumReply.thread_id == thread_id,
                ForumReply.status == ForumReplyStatus.completed,
                ForumReply.id != reply_id,
            )
            .order_by(ForumReply.created_at.desc())
            .limit(10)
            .all()
        )

        # Build context for LLM
        reply_context = []
        for r in reversed(recent_replies):  # Chronological order
            reply_context.append({
                "author_name": get_reply_author_name(r),
                "content": r.content,
            })

        # Build the prompt with emphasis on responding to the user's message
        system_prompt = build_persona_prompt(
            persona=persona,
            thread_title=thread.title,
            thread_content=thread.content,
            recent_replies=reply_context,
        )

        # Add specific instruction to respond to the user's message
        user_message_prompt = (
            f"A user just replied with this message:\n\n"
            f'"{user_reply_content}"\n\n'
            f"Write a direct response to their message, engaging with what they said."
        )

        try:
            # Generate response using LLM
            content = execute_text_task_plain(
                messages=[{"role": "user", "content": user_message_prompt}],
                system_prompt=system_prompt,
            )

            # Update reply with content
            reply.content = content
            reply.status = ForumReplyStatus.completed

            # Update thread's updated_at
            thread.updated_at = datetime.now(UTC)

            db.commit()

            logger.info(
                f"[{task_id}] {persona.name} direct reply generated successfully"
            )

            return {
                "success": True,
                "reply_id": reply_id,
                "persona_name": persona.name,
                "content": content,
            }

        except Exception as e:
            logger.error(f"[{task_id}] Failed to generate reply: {e}", exc_info=True)
            reply.status = ForumReplyStatus.failed
            reply.content = "Error generating response"
            db.commit()

            return {"success": False, "error": str(e)}
