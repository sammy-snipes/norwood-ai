"""Base schema for LLM responses."""

from pydantic import BaseModel, ConfigDict


class LLMSchema(BaseModel):
    """Base class for all LLM response schemas."""

    model_config = ConfigDict(extra="forbid")
