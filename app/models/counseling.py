from enum import Enum as PyEnum

from sqlalchemy import Column, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base, TimestampMixin


class MessageStatus(str, PyEnum):
    """Status of a counseling message."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class MessageRole(str, PyEnum):
    """Role of a message sender."""

    user = "user"
    assistant = "assistant"


class CounselingSession(Base, TimestampMixin):
    """A counseling chat session."""

    __tablename__ = "counseling_sessions"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)  # Auto-generated or user-set

    # Relationships
    user = relationship("User", back_populates="counseling_sessions")
    messages = relationship(
        "CounselingMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CounselingMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<CounselingSession {self.id}>"


class CounselingMessage(Base, TimestampMixin):
    """A message in a counseling session."""

    __tablename__ = "counseling_messages"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    session_id = Column(
        String(26), ForeignKey("counseling_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=True)  # Nullable for pending assistant messages
    status = Column(Enum(MessageStatus), nullable=False, default=MessageStatus.completed)

    # Relationships
    session = relationship("CounselingSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<CounselingMessage {self.id} ({self.role}, {self.status})>"
