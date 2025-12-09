"""Counseling chat router - premium only."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.routers.auth import decode_token
from app.services import counseling as counseling_service
from app.tasks.counseling import generate_counseling_response_task

router = APIRouter(prefix="/api/counseling", tags=["counseling"])


# Schemas
class SessionResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    message_count: int

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    messages: list[MessageResponse]


class SendMessageRequest(BaseModel):
    content: str


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    task_id: str


class MessageStatusResponse(BaseModel):
    id: str
    status: str
    content: str | None


# Dependencies
def require_premium(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Require premium or admin user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_premium and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Counseling requires a premium subscription",
        )

    return user


# Routes
@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """List all counseling sessions for the user."""
    sessions = counseling_service.list_sessions(user, db)
    return [SessionResponse(**s) for s in sessions]


@router.post("/sessions", response_model=SessionResponse)
def create_session(
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Create a new counseling session."""
    session = counseling_service.create_session(user, db)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        message_count=0,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get a session with all messages."""
    session = counseling_service.get_session_by_id(session_id, user, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    detail = counseling_service.get_session_detail(session)
    return SessionDetailResponse(
        id=detail["id"],
        title=detail["title"],
        created_at=detail["created_at"],
        messages=[MessageResponse(**m) for m in detail["messages"]],
    )


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str,
    request: SendMessageRequest,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Send a message and queue Claude's response."""
    session = counseling_service.get_session_by_id(session_id, user, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg, assistant_msg = counseling_service.send_message(session, request.content, db)

    # Queue the Celery task
    task = generate_counseling_response_task.delay(
        message_id=assistant_msg.id,
        session_id=session.id,
        user_id=user.id,
    )

    return SendMessageResponse(
        user_message=MessageResponse(
            id=user_msg.id,
            role=user_msg.role,
            content=user_msg.content,
            status=user_msg.status,
            created_at=user_msg.created_at,
        ),
        assistant_message=MessageResponse(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            status=assistant_msg.status,
            created_at=assistant_msg.created_at,
        ),
        task_id=task.id,
    )


@router.get("/messages/{message_id}/status", response_model=MessageStatusResponse)
def get_message_status(
    message_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Poll for message status (used for async responses)."""
    status_data = counseling_service.get_message_status(message_id, user, db)
    if not status_data:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageStatusResponse(**status_data)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Delete a counseling session."""
    deleted = counseling_service.delete_session(session_id, user, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}
