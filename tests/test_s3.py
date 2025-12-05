"""Tests for S3 service - runs against real S3."""

import base64
import os

import pytest

from app.services.s3 import S3Service

# Skip if S3 not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("S3_BUCKET_NAME"), reason="S3_BUCKET_NAME not set"
)


@pytest.fixture
def s3_service():
    return S3Service()


@pytest.fixture
def sample_image_bytes():
    """1x1 red PNG image."""
    # Minimal valid PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )


@pytest.fixture
def sample_image_base64():
    """1x1 red PNG as base64."""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="


class TestS3Service:
    def test_upload_image(self, s3_service, sample_image_bytes):
        """Test uploading raw bytes to S3."""
        key = s3_service.upload_image(
            image_data=sample_image_bytes,
            user_id="test-user-123",
            content_type="image/png",
        )

        assert key.startswith("users/test-user-123/analyses/")
        assert key.endswith(".png")

        # Cleanup
        s3_service.delete_image(key)

    def test_upload_base64_image(self, s3_service, sample_image_base64):
        """Test uploading base64-encoded image to S3."""
        key = s3_service.upload_base64_image(
            base64_data=sample_image_base64,
            user_id="test-user-456",
            content_type="image/png",
        )

        assert key.startswith("users/test-user-456/analyses/")
        assert key.endswith(".png")

        # Cleanup
        s3_service.delete_image(key)

    def test_presigned_url(self, s3_service, sample_image_bytes):
        """Test generating presigned URLs."""
        # Upload first
        key = s3_service.upload_image(
            image_data=sample_image_bytes,
            user_id="test-user-789",
            content_type="image/png",
        )

        # Generate presigned URL
        url = s3_service.get_presigned_url(key, expires_in=60)

        assert "https://" in url
        assert s3_service.bucket_name in url
        assert key in url

        # Cleanup
        s3_service.delete_image(key)

    def test_delete_image(self, s3_service, sample_image_bytes):
        """Test deleting an image."""
        key = s3_service.upload_image(
            image_data=sample_image_bytes,
            user_id="test-user-delete",
            content_type="image/png",
        )

        result = s3_service.delete_image(key)
        assert result is True

    def test_jpeg_extension(self, s3_service, sample_image_bytes):
        """Test that jpeg content type produces .jpg extension."""
        key = s3_service.upload_image(
            image_data=sample_image_bytes,
            user_id="test-user-jpg",
            content_type="image/jpeg",
        )

        assert key.endswith(".jpg")

        # Cleanup
        s3_service.delete_image(key)
