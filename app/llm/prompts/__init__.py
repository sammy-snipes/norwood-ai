"""LLM prompts."""

from app.llm.prompts.analysis import NORWOOD_ANALYSIS_PROMPT
from app.llm.prompts.certification import (
    CERTIFICATION_DIAGNOSIS_PROMPT,
    PHOTO_VALIDATION_PROMPT,
)
from app.llm.prompts.cock import COCK_ANALYSIS_PROMPT
from app.llm.prompts.counseling import build_counseling_prompt
from app.llm.prompts.forum import AGENT_PERSONALITIES, build_forum_agent_prompt, get_agent_display_name

__all__ = [
    "NORWOOD_ANALYSIS_PROMPT",
    "PHOTO_VALIDATION_PROMPT",
    "CERTIFICATION_DIAGNOSIS_PROMPT",
    "COCK_ANALYSIS_PROMPT",
    "build_counseling_prompt",
    "AGENT_PERSONALITIES",
    "build_forum_agent_prompt",
    "get_agent_display_name",
]
