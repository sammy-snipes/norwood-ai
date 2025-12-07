"""
Core LLM execution functions with Pydantic structured output.

Uses tool forcing for guaranteed schema compliance.
"""

import logging
from typing import TypeVar

from pydantic import BaseModel

from app.llm.client import get_client

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def execute_vision_task(
    images: list[tuple[str, str]],  # [(base64_data, media_type), ...]
    system_prompt: str,
    response_model: type[T],
    user_text: str = "Analyze the provided image(s).",
    model: str = DEFAULT_MODEL,
) -> T:
    """
    Send images to Claude, return validated Pydantic model.

    Uses tool forcing to guarantee structured output matching response_model schema.

    Args:
        images: List of (base64_data, media_type) tuples
        system_prompt: System instructions for the model
        response_model: Pydantic model class for response validation
        user_text: Text prompt accompanying the images
        model: Model identifier to use

    Returns:
        Validated Pydantic model instance
    """
    client = get_client()

    # Build content blocks
    content = []
    for base64_data, media_type in images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                },
            }
        )
    content.append({"type": "text", "text": user_text})

    # Define tool from Pydantic schema
    tool_name = response_model.__name__
    tool = {
        "name": tool_name,
        "description": f"Return the {tool_name} result",
        "input_schema": response_model.model_json_schema(),
    }

    logger.debug(f"Executing vision task with model={model}, tool={tool_name}")

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": content}],
    )

    # Extract tool use block
    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )

    if not tool_use:
        logger.error(f"No tool use in response: {response.content}")
        raise ValueError("No tool use in response")

    return response_model.model_validate(tool_use.input)


def execute_text_task(
    messages: list[dict],  # [{"role": "user"|"assistant", "content": str}, ...]
    system_prompt: str,
    response_model: type[T],
    model: str = DEFAULT_MODEL,
) -> T:
    """
    Send text conversation, return validated Pydantic model.

    Args:
        messages: Conversation history
        system_prompt: System instructions for the model
        response_model: Pydantic model class for response validation
        model: Model identifier to use

    Returns:
        Validated Pydantic model instance
    """
    client = get_client()

    tool_name = response_model.__name__
    tool = {
        "name": tool_name,
        "description": f"Return the {tool_name} result",
        "input_schema": response_model.model_json_schema(),
    }

    logger.debug(f"Executing text task with model={model}, tool={tool_name}")

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=messages,
    )

    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )

    if not tool_use:
        logger.error(f"No tool use in response: {response.content}")
        raise ValueError("No tool use in response")

    return response_model.model_validate(tool_use.input)


def execute_text_task_plain(
    messages: list[dict],
    system_prompt: str,
    model: str = DEFAULT_MODEL,
    context_images: list[tuple[str, str]] | None = None,
) -> str:
    """
    Send text conversation, return plain text response.

    For cases where structured output isn't needed (e.g., counseling chat).

    Args:
        messages: Conversation history
        system_prompt: System instructions for the model
        model: Model identifier to use
        context_images: Optional list of (base64_data, media_type) to prepend as context

    Returns:
        Plain text response string
    """
    client = get_client()

    logger.debug(f"Executing plain text task with model={model}")

    # If context images provided, prepend as a user message
    final_messages = []
    if context_images:
        content = []
        for base64_data, media_type in context_images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data,
                    },
                }
            )
        content.append(
            {"type": "text", "text": "Here is the Norwood scale reference chart for context."}
        )
        final_messages.append({"role": "user", "content": content})
        final_messages.append(
            {
                "role": "assistant",
                "content": "Thank you for the reference chart. I'll use this to inform our conversation about hair loss.",
            }
        )

    final_messages.extend(messages)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=final_messages,
    )

    text_block = next(
        (block for block in response.content if block.type == "text"),
        None,
    )

    if not text_block:
        logger.error(f"No text in response: {response.content}")
        raise ValueError("No text in response")

    return text_block.text
