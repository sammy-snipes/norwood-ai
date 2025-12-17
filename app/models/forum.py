"""Forum models for message board feature."""

from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base, TimestampMixin


class AgentType(str, PyEnum):
    """Type of AI agent personality (legacy - use ForumPersona instead)."""

    expert = "expert"
    comedian = "comedian"
    kind = "kind"
    jerk = "jerk"


class ForumReplyStatus(str, PyEnum):
    """Status of a forum reply."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ForumPersona(Base, TimestampMixin):
    """A persona/personality for AI agents in the forum."""

    __tablename__ = "forum_personas"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    replies = relationship("ForumReply", back_populates="persona")
    schedules = relationship("ForumAgentSchedule", back_populates="persona")

    def __repr__(self) -> str:
        return f"<ForumPersona {self.id}: {self.name}>"


class ForumThread(Base, TimestampMixin):
    """A forum discussion thread."""

    __tablename__ = "forum_threads"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="forum_threads")
    replies = relationship(
        "ForumReply",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ForumReply.created_at",
    )
    agent_schedules = relationship(
        "ForumAgentSchedule",
        back_populates="thread",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ForumThread {self.id}: {self.title[:30]}>"


class ForumReply(Base, TimestampMixin):
    """A reply in a forum thread."""

    __tablename__ = "forum_replies"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    thread_id = Column(String(26), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(String(26), ForeignKey("forum_replies.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=True)  # Nullable for pending agent replies
    status = Column(Enum(ForumReplyStatus), nullable=False, default=ForumReplyStatus.completed)
    agent_type = Column(Enum(AgentType), nullable=True)  # Legacy - use persona_id
    persona_id = Column(String(26), ForeignKey("forum_personas.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    thread = relationship("ForumThread", back_populates="replies")
    user = relationship("User", back_populates="forum_replies")
    parent = relationship("ForumReply", remote_side=[id], backref="children")
    persona = relationship("ForumPersona", back_populates="replies")

    @property
    def is_agent_reply(self) -> bool:
        """Check if this reply is from an AI agent (persona or legacy agent_type)."""
        return self.persona_id is not None or self.agent_type is not None

    @property
    def display_name(self) -> str | None:
        """Get display name for agent replies."""
        if self.persona:
            return self.persona.name
        return None

    def __repr__(self) -> str:
        author = self.persona_id or self.agent_type or "user"
        return f"<ForumReply {self.id} ({author}, {self.status})>"


class ForumAgentSchedule(Base, TimestampMixin):
    """Schedule for AI agent replies with exponential backoff."""

    __tablename__ = "forum_agent_schedules"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    thread_id = Column(String(26), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(Enum(AgentType), nullable=True)  # Legacy - use persona_id
    persona_id = Column(String(26), ForeignKey("forum_personas.id", ondelete="CASCADE"), nullable=True)
    next_reply_at = Column(DateTime(timezone=True), nullable=True)
    reply_count = Column(Integer, default=0, nullable=False)
    last_replied_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    thread = relationship("ForumThread", back_populates="agent_schedules")
    persona = relationship("ForumPersona", back_populates="schedules")

    __table_args__ = (
        UniqueConstraint("thread_id", "agent_type", name="uq_agent_schedule_thread_agent"),
    )

    def __repr__(self) -> str:
        name = self.persona.name if self.persona else self.agent_type
        return f"<ForumAgentSchedule {name} for thread {self.thread_id}>"
