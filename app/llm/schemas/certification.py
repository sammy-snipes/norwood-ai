"""Schemas for Norwood Certification feature."""

from pydantic import Field

from app.llm.schemas.base import LLMSchema


class PhotoValidationResult(LLMSchema):
    """Result from validating a certification photo."""

    approved: bool = Field(description="Whether the photo meets quality requirements")
    rejection_reason: str | None = Field(
        default=None,
        description="If rejected, why. E.g., 'Hairline obscured by hat'",
    )
    quality_notes: str = Field(
        description="What was observed about photo quality and hairline visibility"
    )


class CertificationDiagnosis(LLMSchema):
    """Clinical Norwood diagnosis from 3 validated photos."""

    norwood_stage: int = Field(ge=1, le=7, description="Norwood-Hamilton stage from 1-7")
    norwood_variant: str | None = Field(
        default=None,
        description="Variant if applicable: 'A' (anterior) or 'V' (vertex)",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    clinical_assessment: str = Field(description="Formal clinical assessment in medical language")
    observable_features: list[str] = Field(
        description="List of observed features supporting the diagnosis"
    )
    differential_considerations: str = Field(
        description="Why this stage vs adjacent stages, ruling out alternatives"
    )
