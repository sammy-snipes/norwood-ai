"""Reference assets for LLM grounding."""

import base64
from functools import lru_cache
from pathlib import Path

ASSETS_DIR = Path(__file__).parent


@lru_cache(maxsize=10)
def load_reference_image(filename: str) -> tuple[str, str]:
    """
    Load a reference image as base64.

    Returns:
        Tuple of (base64_data, media_type)
    """
    filepath = ASSETS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Reference image not found: {filename}")

    # Determine media type from extension
    ext = filepath.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "image/png")

    with open(filepath, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    return (data, media_type)


def get_norwood_chart() -> tuple[str, str]:
    """Get the Norwood scale reference chart."""
    return load_reference_image("norwood.png")


def get_cock_chart() -> tuple[str, str]:
    """Get the cock rating reference chart."""
    return load_reference_image("cock.jpg")
