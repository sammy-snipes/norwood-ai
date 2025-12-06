"""Schema for Norwood analysis (existing feature)."""

from pydantic import Field

from app.llm.schemas.base import LLMSchema


class NorwoodAnalysisResult(LLMSchema):
    """Result from analyzing a single photo for Norwood stage."""

    norwood_stage: int = Field(ge=1, le=7, description="Norwood stage from 1-7")
    confidence: str = Field(description="Confidence level: high, medium, or low")
    title: str = Field(max_length=100, description="Punchy, memorable title for the analysis")
    description: str = Field(
        description="Brief, matter-of-fact description of their hair situation"
    )
    analysis_text: str = Field(description="Philosophical reflection on the diagnosis, stoic tone")
    reasoning: str = Field(description="Clinical observations that led to this diagnosis")
