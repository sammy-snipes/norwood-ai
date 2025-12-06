"""Certification models."""

import enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ulid import ULID

from app.models.base import Base, TimestampMixin


class PhotoType(str, enum.Enum):
    """Type of certification photo."""

    front = "front"
    left = "left"
    right = "right"


class ValidationStatus(str, enum.Enum):
    """Status of photo validation."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class CertificationStatus(str, enum.Enum):
    """Status of certification process."""

    photos_pending = "photos_pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class CertificationPhoto(Base):
    """Photo submitted for certification."""

    __tablename__ = "certification_photos"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    certification_id = Column(
        String(26),
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_type = Column(SAEnum(PhotoType), nullable=False)
    s3_key = Column(Text, nullable=False)
    validation_status = Column(
        SAEnum(ValidationStatus),
        nullable=False,
        default=ValidationStatus.pending,
    )
    rejection_reason = Column(Text, nullable=True)
    quality_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    certification = relationship("Certification", back_populates="photos")

    def __repr__(self) -> str:
        return f"<CertificationPhoto {self.photo_type.value} - {self.validation_status.value}>"


class Certification(Base, TimestampMixin):
    """Norwood certification record."""

    __tablename__ = "certifications"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SAEnum(CertificationStatus),
        nullable=False,
        default=CertificationStatus.photos_pending,
    )
    norwood_stage = Column(Integer, nullable=True)
    norwood_variant = Column(String(5), nullable=True)
    confidence = Column(Float, nullable=True)
    clinical_assessment = Column(Text, nullable=True)
    observable_features = Column(JSONB, nullable=True)
    differential_considerations = Column(Text, nullable=True)
    pdf_s3_key = Column(Text, nullable=True)
    certified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="certifications")
    photos = relationship(
        "CertificationPhoto",
        back_populates="certification",
        cascade="all, delete-orphan",
        order_by="CertificationPhoto.created_at",
    )

    def __repr__(self) -> str:
        return f"<Certification {self.id} - {self.status.value}>"
