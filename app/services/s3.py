import base64
import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for uploading and retrieving images from S3."""

    def __init__(self, bucket_name: str | None = None, region: str | None = None):
        settings = get_settings()
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region = region or settings.AWS_REGION
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def upload_image(
        self,
        image_data: bytes,
        user_id: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """
        Upload an image to S3.

        Args:
            image_data: Raw image bytes
            user_id: User ID for organizing uploads
            content_type: MIME type of the image

        Returns:
            S3 key (path) of the uploaded image
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")

        # Generate unique key: users/{user_id}/analyses/{timestamp}.{ext}
        ext = content_type.split("/")[-1]
        if ext == "jpeg":
            ext = "jpg"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        key = f"users/{user_id}/analyses/{timestamp}.{ext}"

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType=content_type,
            )
            logger.info(f"Uploaded image to s3://{self.bucket_name}/{key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    def upload_base64_image(
        self,
        base64_data: str,
        user_id: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """
        Upload a base64-encoded image to S3.

        Args:
            base64_data: Base64-encoded image data
            user_id: User ID for organizing uploads
            content_type: MIME type of the image

        Returns:
            S3 key (path) of the uploaded image
        """
        image_data = base64.b64decode(base64_data)
        return self.upload_image(image_data, user_id, content_type)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access to an image.

        Args:
            key: S3 key of the image
            expires_in: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def delete_image(self, key: str) -> bool:
        """
        Delete an image from S3.

        Args:
            key: S3 key of the image

        Returns:
            True if deleted successfully
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            raise

    def get_image_base64(self, key: str) -> tuple[str, str]:
        """
        Fetch an image from S3 and return as base64.

        Args:
            key: S3 key of the image

        Returns:
            Tuple of (base64_data, content_type)
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")

        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            image_data = response["Body"].read()
            content_type = response.get("ContentType", "image/jpeg")
            base64_data = base64.b64encode(image_data).decode("utf-8")
            return base64_data, content_type
        except ClientError as e:
            logger.error(f"Failed to get image from S3: {e}")
            raise

    def upload_pdf(self, pdf_data: bytes, user_id: str, filename: str) -> str:
        """
        Upload a PDF to S3.

        Args:
            pdf_data: PDF file bytes
            user_id: User ID for organizing uploads
            filename: Filename for the PDF

        Returns:
            S3 key (path) of the uploaded PDF
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")

        key = f"users/{user_id}/certifications/{filename}"

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=pdf_data,
                ContentType="application/pdf",
            )
            logger.info(f"Uploaded PDF to s3://{self.bucket_name}/{key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to upload PDF to S3: {e}")
            raise

    def upload_base64_image_with_prefix(
        self,
        base64_data: str,
        user_id: str,
        content_type: str,
        prefix: str,
    ) -> str:
        """
        Upload a base64-encoded image to S3 with a custom prefix.

        Args:
            base64_data: Base64-encoded image data
            user_id: User ID for organizing uploads
            content_type: MIME type of the image
            prefix: Custom prefix path (e.g., 'certifications/abc123')

        Returns:
            S3 key (path) of the uploaded image
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")

        image_data = base64.b64decode(base64_data)

        ext = content_type.split("/")[-1]
        if ext == "jpeg":
            ext = "jpg"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        key = f"users/{user_id}/{prefix}/{timestamp}.{ext}"

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType=content_type,
            )
            logger.info(f"Uploaded image to s3://{self.bucket_name}/{key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
