"""Anthropic client singleton."""

from functools import lru_cache

import anthropic

from app.config import get_settings


@lru_cache
def get_client() -> anthropic.Anthropic:
    """Get or create the Anthropic client singleton."""
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
