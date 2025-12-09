"""Counseling service for managing counseling sessions and messages."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CounselingMessage, CounselingSession, User
from app.models.counseling import MessageRole, MessageStatus

logger = logging.getLogger(__name__)
settings = get_settings()


def list_sessions(user: User, db: Session) -> list[dict]:
    """List all counseling sessions for the user."""
    sessions = (
        db.query(CounselingSession)
        .filter(CounselingSession.user_id == user.id)
        .order_by(CounselingSession.updated_at.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "message_count": len(s.messages),
        }
        for s in sessions
    ]


def create_session(user: User, db: Session) -> CounselingSession:
    """Create a new counseling session."""
    session = CounselingSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Created counseling session {session.id} for user {user.id}")
    return session


def get_session_by_id(session_id: str, user: User, db: Session) -> CounselingSession | None:
    """Get a session by ID for the given user."""
    return (
        db.query(CounselingSession)
        .filter(CounselingSession.id == session_id, CounselingSession.user_id == user.id)
        .first()
    )


def get_session_detail(session: CounselingSession) -> dict:
    """Get session with all messages sorted by creation time."""
    sorted_messages = sorted(session.messages, key=lambda m: (m.created_at, m.id))

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "status": m.status,
                "created_at": m.created_at,
            }
            for m in sorted_messages
        ],
    }


def send_message(
    session: CounselingSession, content: str, db: Session
) -> tuple[CounselingMessage, CounselingMessage]:
    """
    Create user message and pending assistant message.

    Returns tuple of (user_message, assistant_message).
    """
    # Save user message (completed immediately)
    user_msg = CounselingMessage(
        session_id=session.id,
        role=MessageRole.user,
        content=content,
        status=MessageStatus.completed,
    )
    db.add(user_msg)

    # Auto-generate title from first message if not set
    if not session.title:
        words = content.split()[:5]
        session.title = " ".join(words) + ("..." if len(words) == 5 else "")

    db.commit()
    db.refresh(user_msg)

    # Create pending assistant message (separate transaction for different timestamp)
    assistant_msg = CounselingMessage(
        session_id=session.id,
        role=MessageRole.assistant,
        content=None,
        status=MessageStatus.pending,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return user_msg, assistant_msg


def get_message_status(message_id: str, user: User, db: Session) -> dict | None:
    """Get message status for async polling."""
    message = (
        db.query(CounselingMessage)
        .join(CounselingSession)
        .filter(
            CounselingMessage.id == message_id,
            CounselingSession.user_id == user.id,
        )
        .first()
    )

    if not message:
        return None

    return {
        "id": message.id,
        "status": message.status,
        "content": message.content,
    }


def delete_session(session_id: str, user: User, db: Session) -> bool:
    """Delete a counseling session."""
    session = get_session_by_id(session_id, user, db)

    if not session:
        return False

    db.delete(session)
    db.commit()
    logger.info(f"Deleted counseling session {session_id}")

    return True
