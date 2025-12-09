import base64
import io
import logging
from typing import Literal

from PIL import Image

logger = logging.getLogger(__name__)

# Claude's optimal image dimension - images larger than this get downsampled anyway
CLAUDE_MAX_DIMENSION = 1568

# HEIC/HEIF support - lazy loaded to avoid import errors if not installed
_heif_registered = False


def _ensure_heif_support():
    """Register HEIF plugin with Pillow if available."""
    global _heif_registered
    if not _heif_registered:
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
            _heif_registered = True
            logger.debug("HEIF support registered")
        except ImportError:
            logger.warning("pillow-heif not installed, HEIC images will not be supported")
            _heif_registered = True  # Don't try again


def _is_heic(content_type: str, data: bytes) -> bool:
    """Check if image is HEIC format by content type or magic bytes."""
    if content_type.lower() in ("image/heic", "image/heif"):
        return True
    # Check magic bytes for HEIC: ftyp followed by heic, heix, hevc, or mif1
    if len(data) >= 12:
        ftyp = data[4:8]
        brand = data[8:12]
        if ftyp == b"ftyp" and brand in (b"heic", b"heix", b"hevc", b"mif1"):
            return True
    return False


def process_image_for_claude(
    image_data: bytes,
    content_type: str,
    max_dimension: int = CLAUDE_MAX_DIMENSION,
    output_format: Literal["JPEG", "PNG"] = "JPEG",
    jpeg_quality: int = 85,
) -> tuple[str, str]:
    """
    Process an image for Claude API consumption.

    Handles:
    1. HEIC/HEIF conversion to JPEG/PNG
    2. Downsampling to max dimension while preserving aspect ratio
    3. Base64 encoding

    Args:
        image_data: Raw image bytes
        content_type: Original MIME type (e.g., "image/jpeg", "image/heic")
        max_dimension: Maximum width/height in pixels (default: 1568 for Claude)
        output_format: Output format for converted images ("JPEG" or "PNG")
        jpeg_quality: JPEG quality for output (1-100, default 85)

    Returns:
        Tuple of (base64_encoded_data, output_content_type)

    Raises:
        ValueError: If image cannot be processed
    """
    _ensure_heif_support()

    input_size = len(image_data)
    logger.info(f"Processing image: content_type={content_type}, input_size={input_size} bytes")

    is_heic = _is_heic(content_type, image_data)
    if is_heic:
        logger.info("Detected HEIC/HEIF format, will convert")

    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception as e:
        logger.error(f"Failed to open image: {e}")
        raise ValueError(f"Failed to open image: {e}") from e

    # Track if we need to re-encode
    needs_conversion = is_heic
    original_format = img.format
    original_mode = img.mode
    width, height = img.size

    logger.info(f"Image opened: format={original_format}, mode={original_mode}, size={width}x{height}")

    # Convert RGBA to RGB for JPEG output
    if output_format == "JPEG" and img.mode in ("RGBA", "P"):
        logger.info(f"Converting color mode: {img.mode} -> RGB")
        img = img.convert("RGB")
        needs_conversion = True

    # Check if downsampling is needed
    if width > max_dimension or height > max_dimension:
        # Calculate new size preserving aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        needs_conversion = True
        logger.info(f"Downsampled image from {width}x{height} to {new_width}x{new_height}")

    # If no conversion needed and format is already Claude-compatible, return as-is
    if not needs_conversion and original_format in ("JPEG", "PNG", "GIF", "WEBP"):
        logger.info(f"No conversion needed, returning original {original_format}")
        base64_data = base64.standard_b64encode(image_data).decode("utf-8")
        return base64_data, content_type

    # Re-encode the image
    logger.info(f"Re-encoding image to {output_format}")
    output_buffer = io.BytesIO()
    if output_format == "JPEG":
        img.save(output_buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        output_content_type = "image/jpeg"
    else:
        img.save(output_buffer, format="PNG", optimize=True)
        output_content_type = "image/png"

    output_data = output_buffer.getvalue()
    base64_data = base64.standard_b64encode(output_data).decode("utf-8")

    compression_ratio = (1 - len(output_data) / input_size) * 100 if input_size > 0 else 0
    logger.info(
        f"Image processing complete: {content_type} -> {output_content_type}, "
        f"{input_size} -> {len(output_data)} bytes ({compression_ratio:.1f}% reduction)"
    )

    return base64_data, output_content_type


def process_base64_image_for_claude(
    base64_data: str,
    content_type: str,
    max_dimension: int = CLAUDE_MAX_DIMENSION,
    output_format: Literal["JPEG", "PNG"] = "JPEG",
    jpeg_quality: int = 85,
) -> tuple[str, str]:
    """
    Process a base64-encoded image for Claude API consumption.

    Convenience wrapper around process_image_for_claude for base64 input.

    Args:
        base64_data: Base64-encoded image data
        content_type: Original MIME type
        max_dimension: Maximum width/height in pixels
        output_format: Output format for converted images
        jpeg_quality: JPEG quality for output

    Returns:
        Tuple of (base64_encoded_data, output_content_type)
    """
    logger.info(f"Processing base64 image: content_type={content_type}, base64_len={len(base64_data)}")
    image_data = base64.b64decode(base64_data)
    return process_image_for_claude(
        image_data=image_data,
        content_type=content_type,
        max_dimension=max_dimension,
        output_format=output_format,
        jpeg_quality=jpeg_quality,
    )
