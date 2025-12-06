from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_premium = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    free_analyses_remaining = Column(Integer, default=1, nullable=False)
    options = Column(JSONB, default=dict, nullable=False)

    # Relationships
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    counseling_sessions = relationship(
        "CounselingSession", back_populates="user", cascade="all, delete-orphan"
    )
    certifications = relationship(
        "Certification", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
