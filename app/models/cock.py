"""Cock certification models."""

import enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from ulid import ULID

from app.models.base import Base, TimestampMixin


class CockCertificationStatus(str, enum.Enum):
    """Status of cock certification process."""

    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class CockSizeCategory(str, enum.Enum):
    """Size category based on standard deviations."""

    micro = "micro"
    below_average = "below_average"
    average = "average"
    above_average = "above_average"
    large = "large"
    monster = "monster"


class PleasureZone(str, enum.Enum):
    """Female pleasure zone from the chart."""

    A = "ideal"
    B = "very_satisfying"
    C = "satisfying"
    D = "enjoyable"
    E = "not_satisfying"


class CockCertification(Base, TimestampMixin):
    """Cock certification record."""

    __tablename__ = "cock_certifications"

    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SAEnum(CockCertificationStatus),
        nullable=False,
        default=CockCertificationStatus.pending,
    )

    # Image
    s3_key = Column(Text, nullable=True)

    # Measurements (estimated by Claude)
    length_inches = Column(Float, nullable=True)
    girth_inches = Column(Float, nullable=True)

    # Calculated results
    size_category = Column(SAEnum(CockSizeCategory), nullable=True)
    pleasure_zone = Column(SAEnum(PleasureZone), nullable=True)
    pleasure_zone_label = Column(String(50), nullable=True)

    # Claude's assessment
    description = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    reference_objects_used = Column(Text, nullable=True)

    # PDF
    pdf_s3_key = Column(Text, nullable=True)
    certified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="cock_certifications")

    def __repr__(self) -> str:
        return f"<CockCertification {self.id} - {self.status.value}>"


# Statistical constants for size categorization
# Based on studies: avg length ~5.5", avg girth ~4.6"
AVG_LENGTH = 5.5
AVG_GIRTH = 4.6
STD_LENGTH = 0.7
STD_GIRTH = 0.5


def calculate_size_category(length: float, girth: float) -> CockSizeCategory:
    """Calculate size category based on standard deviations from mean."""
    # Combined z-score (average of length and girth z-scores)
    length_z = (length - AVG_LENGTH) / STD_LENGTH
    girth_z = (girth - AVG_GIRTH) / STD_GIRTH
    combined_z = (length_z + girth_z) / 2

    if combined_z < -2:
        return CockSizeCategory.micro
    elif combined_z < -1:
        return CockSizeCategory.below_average
    elif combined_z < 1:
        return CockSizeCategory.average
    elif combined_z < 2:
        return CockSizeCategory.above_average
    elif combined_z < 3:
        return CockSizeCategory.large
    else:
        return CockSizeCategory.monster


def calculate_pleasure_zone(length: float, girth: float) -> tuple[PleasureZone, str]:
    """
    Calculate pleasure zone based on the chart.

    Returns (PleasureZone enum, human-readable label)
    """
    # Chart zones (approximate from the image):
    # A (ideal/perfect): length 7-8", girth 6-6.5"
    # B (very satisfying): surrounding A, length 6.5-8.5", girth 5.5-7"
    # C (satisfying): wider range around B
    # D (enjoyable): even wider
    # E (not satisfying): edges - too small, too big, or weird combos

    # Zone A: ideal (red zone in chart)
    if 7 <= length <= 8 and 6 <= girth <= 6.5:
        return PleasureZone.A, "Ideal (Perfect)"

    # Zone B: very satisfying (green zone)
    if 6 <= length <= 8.5 and 5.5 <= girth <= 7:
        return PleasureZone.B, "Very Satisfying But Not Ideal"

    # Zone C: satisfying (yellow zone)
    if 5.5 <= length <= 9 and 5 <= girth <= 7.5:
        return PleasureZone.C, "Satisfying"

    # Zone D: enjoyable (blue zone)
    if 5 <= length <= 9.5 and 4.5 <= girth <= 8:
        return PleasureZone.D, "Enjoyable"

    # Zone E: not satisfying (white - too extreme)
    return PleasureZone.E, "Not Satisfying"


SIZE_CATEGORY_LABELS = {
    CockSizeCategory.micro: "Micro",
    CockSizeCategory.below_average: "Below Average",
    CockSizeCategory.average: "Average",
    CockSizeCategory.above_average: "Above Average",
    CockSizeCategory.large: "Rather Large",
    CockSizeCategory.monster: "Monster",
}
