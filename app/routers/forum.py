"""Forum router - message board for all authenticated users."""

import random
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ForumReply, ForumReplyStatus, ForumThread, User
from app.routers.auth import decode_token
from app.tasks.forum import (
    bump_agent_schedules_on_user_reply_task,
    generate_direct_agent_reply_task,
    initialize_forum_agent_schedules_task,
)

router = APIRouter(prefix="/api/forum", tags=["forum"])


# --- Schemas ---


class UserBrief(BaseModel):
    """Brief user info for display."""

    id: str
    name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


class AgentInfo(BaseModel):
    """Agent info for display."""

    agent_type: str
    display_name: str


class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)


class CreateReplyRequest(BaseModel):
    """Request to create a reply."""

    content: str = Field(..., min_length=1, max_length=5000)


class ReplyResponse(BaseModel):
    """A single reply."""

    id: str
    content: str | None
    status: str
    user: UserBrief | None
    agent: AgentInfo | None
    parent_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadListItem(BaseModel):
    """Thread summary for list view."""

    id: str
    title: str
    user: UserBrief
    created_at: datetime
    reply_count: int
    last_activity_at: datetime
    is_pinned: bool


class ThreadDetailResponse(BaseModel):
    """Full thread with replies."""

    id: str
    title: str
    content: str
    user: UserBrief
    created_at: datetime
    is_pinned: bool
    replies: list[ReplyResponse]


class ThreadListResponse(BaseModel):
    """Paginated thread list."""

    threads: list[ThreadListItem]
    total: int
    page: int
    per_page: int


class ReplyStatusResponse(BaseModel):
    """Status of a pending reply."""

    id: str
    status: str
    content: str | None


# --- Dependencies ---


def require_auth(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Require authenticated user (not premium-only)."""
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

    return user


# --- Helper functions ---


def build_reply_response(reply: ForumReply) -> ReplyResponse:
    """Build a reply response from a ForumReply model."""
    user_brief = None
    agent_info = None

    # Check for persona first (new system), then legacy agent_type
    if reply.persona:
        agent_info = AgentInfo(
            agent_type="persona",
            display_name=reply.persona.name,
        )
    elif reply.agent_type:
        # Legacy support for old agent_type system
        from app.llm.prompts.forum import get_agent_display_name
        agent_info = AgentInfo(
            agent_type=reply.agent_type.value,
            display_name=get_agent_display_name(reply.agent_type),
        )
    elif reply.user:
        user_brief = UserBrief(
            id=reply.user.id,
            name=reply.user.name,
            avatar_url=reply.user.avatar_url,
        )

    return ReplyResponse(
        id=reply.id,
        content=reply.content,
        status=reply.status.value,
        user=user_brief,
        agent=agent_info,
        parent_id=reply.parent_id,
        created_at=reply.created_at,
    )


# --- Routes ---


@router.get("/threads", response_model=ThreadListResponse)
def list_threads(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all forum threads with pagination."""
    offset = (page - 1) * per_page

    # Get total count
    total = db.query(func.count(ForumThread.id)).scalar()

    # Get threads with reply counts and last activity
    threads = (
        db.query(ForumThread)
        .order_by(ForumThread.is_pinned.desc(), ForumThread.updated_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    thread_items = []
    for thread in threads:
        # Count replies
        reply_count = db.query(func.count(ForumReply.id)).filter(ForumReply.thread_id == thread.id).scalar()

        # Get last activity (last reply or thread creation)
        last_reply = (
            db.query(ForumReply)
            .filter(ForumReply.thread_id == thread.id)
            .order_by(ForumReply.created_at.desc())
            .first()
        )
        last_activity = last_reply.created_at if last_reply else thread.created_at

        thread_items.append(
            ThreadListItem(
                id=thread.id,
                title=thread.title,
                user=UserBrief(
                    id=thread.user.id,
                    name=thread.user.name,
                    avatar_url=thread.user.avatar_url,
                ),
                created_at=thread.created_at,
                reply_count=reply_count,
                last_activity_at=last_activity,
                is_pinned=thread.is_pinned,
            )
        )

    return ThreadListResponse(
        threads=thread_items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/threads", response_model=ThreadListItem, status_code=status.HTTP_201_CREATED)
def create_thread(
    request: CreateThreadRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new forum thread."""
    thread = ForumThread(
        user_id=user.id,
        title=request.title,
        content=request.content,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    # Initialize agent schedules asynchronously
    initialize_forum_agent_schedules_task.delay(thread.id)

    return ThreadListItem(
        id=thread.id,
        title=thread.title,
        user=UserBrief(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
        ),
        created_at=thread.created_at,
        reply_count=0,
        last_activity_at=thread.created_at,
        is_pinned=thread.is_pinned,
    )


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get a thread with all its replies."""
    thread = db.query(ForumThread).filter(ForumThread.id == thread_id).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Get all replies sorted by creation time
    replies = (
        db.query(ForumReply)
        .filter(ForumReply.thread_id == thread_id)
        .order_by(ForumReply.created_at)
        .all()
    )

    return ThreadDetailResponse(
        id=thread.id,
        title=thread.title,
        content=thread.content,
        user=UserBrief(
            id=thread.user.id,
            name=thread.user.name,
            avatar_url=thread.user.avatar_url,
        ),
        created_at=thread.created_at,
        is_pinned=thread.is_pinned,
        replies=[build_reply_response(r) for r in replies],
    )


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a thread (owner or admin only)."""
    thread = db.query(ForumThread).filter(ForumThread.id == thread_id).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if thread.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this thread")

    db.delete(thread)
    db.commit()

    return {"success": True}


@router.post("/threads/{thread_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
def create_reply(
    thread_id: str,
    request: CreateReplyRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a reply to a thread."""
    thread = db.query(ForumThread).filter(ForumThread.id == thread_id).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    reply = ForumReply(
        thread_id=thread_id,
        user_id=user.id,
        content=request.content,
        status=ForumReplyStatus.completed,
    )
    db.add(reply)

    # Update thread's updated_at for activity tracking
    thread.updated_at = func.now()

    db.commit()
    db.refresh(reply)

    # Bump agent schedules so they respond within 1-2 minutes
    bump_agent_schedules_on_user_reply_task.delay(thread_id)

    return build_reply_response(reply)


@router.post("/replies/{reply_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
def create_nested_reply(
    reply_id: str,
    request: CreateReplyRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a nested reply to another reply."""
    parent_reply = db.query(ForumReply).filter(ForumReply.id == reply_id).first()

    if not parent_reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    thread = db.query(ForumThread).filter(ForumThread.id == parent_reply.thread_id).first()

    reply = ForumReply(
        thread_id=parent_reply.thread_id,
        user_id=user.id,
        parent_id=reply_id,
        content=request.content,
        status=ForumReplyStatus.completed,
    )
    db.add(reply)

    # Update thread's updated_at for activity tracking
    if thread:
        thread.updated_at = func.now()

    db.commit()
    db.refresh(reply)

    # If replying to an agent's message (persona or legacy agent_type), schedule a direct reply
    if parent_reply.persona_id is not None or parent_reply.agent_type is not None:
        # Agent will reply directly to the user's message within 1-2 minutes
        generate_direct_agent_reply_task.apply_async(
            kwargs={
                "thread_id": parent_reply.thread_id,
                "parent_reply_id": reply.id,
                "user_reply_content": request.content,
            },
            countdown=60 + (30 * random.random()),  # 60-90 seconds
        )
    else:
        # Regular reply - just bump agent schedules
        bump_agent_schedules_on_user_reply_task.delay(parent_reply.thread_id)

    return build_reply_response(reply)


@router.get("/replies/{reply_id}/status", response_model=ReplyStatusResponse)
def get_reply_status(
    reply_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Poll for reply status (used for pending agent replies)."""
    reply = db.query(ForumReply).filter(ForumReply.id == reply_id).first()

    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    return ReplyStatusResponse(
        id=reply.id,
        status=reply.status.value,
        content=reply.content,
    )


@router.delete("/replies/{reply_id}")
def delete_reply(
    reply_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a reply (owner or admin only)."""
    reply = db.query(ForumReply).filter(ForumReply.id == reply_id).first()

    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    if reply.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this reply")

    db.delete(reply)
    db.commit()

    return {"success": True}
