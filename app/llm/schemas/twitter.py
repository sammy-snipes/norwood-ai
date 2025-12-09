"""Schema for Twitter hairline analysis."""

from pydantic import Field

from app.llm.schemas.base import LLMSchema


class TwitterAnalysisResult(LLMSchema):
    """Result from analyzing a photo for Twitter reply."""

    norwood_stage: int = Field(ge=1, le=7, description="Norwood stage from 1-7")
    reply_text: str = Field(max_length=280, description="The reply to post (under 280 chars)")
