"""Schemas for Cock Certification feature."""

from pydantic import Field

from app.llm.schemas.base import LLMSchema


class CockAnalysisResult(LLMSchema):
    """Result from analyzing a cock photo."""

    length_inches: float = Field(
        ge=1.0,
        le=15.0,
        description="Estimated length in inches based on reference objects in image",
    )
    girth_inches: float = Field(
        ge=1.0,
        le=10.0,
        description="Estimated girth/circumference in inches based on reference objects",
    )
    description: str = Field(
        description="Clinical description of the specimen. Be detailed but professional.",
    )
    reference_objects_used: str = Field(
        description="What reference objects in the photo were used to estimate size (e.g., hand, phone, measuring tape, doorframe, etc.)",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in measurements. Higher if clear reference objects are present.",
    )
