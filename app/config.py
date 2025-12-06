import logging
from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    DEV = "dev"
    PROD = "prod"


def _load_secrets_from_aws(region: str = "us-east-1") -> dict[str, str]:
    """Load secrets from AWS Secrets Manager. Returns empty dict on failure."""
    try:
        from app.services.secrets import get_secrets_service

        secrets = get_secrets_service(region).load_all()
        result = {}

        if secrets.google_oauth:
            result["GOOGLE_CLIENT_ID"] = secrets.google_oauth.client_id
            result["GOOGLE_CLIENT_SECRET"] = secrets.google_oauth.client_secret

        if secrets.database:
            result["DATABASE_URL"] = secrets.database.url

        if secrets.s3_bucket_name:
            result["S3_BUCKET_NAME"] = secrets.s3_bucket_name

        if secrets.anthropic_api_key:
            result["ANTHROPIC_API_KEY"] = secrets.anthropic_api_key

        if secrets.jwt_secret_key:
            result["JWT_SECRET_KEY"] = secrets.jwt_secret_key

        if secrets.stripe:
            result["STRIPE_SECRET_KEY"] = secrets.stripe.secret_key
            result["STRIPE_PUBLISHABLE_KEY"] = secrets.stripe.publishable_key
            result["STRIPE_WEBHOOK_SECRET"] = secrets.stripe.webhook_secret
            result["STRIPE_PREMIUM_PRICE_ID"] = secrets.stripe.premium_price_id
            result["STRIPE_SUCCESS_URL"] = secrets.stripe.success_url
            result["STRIPE_CANCEL_URL"] = secrets.stripe.cancel_url

        return result
    except Exception as e:
        logger.warning(f"Failed to load secrets from AWS: {e}")
        return {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core
    ENV: Environment = Environment.DEV
    LOG_LEVEL: str = "INFO"

    # Database (loaded from secrets manager)
    DATABASE_URL: str = ""

    # Redis / Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Anthropic (loaded from secrets manager)
    ANTHROPIC_API_KEY: str = ""

    # Google OAuth (loaded from secrets manager)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # JWT (loaded from secrets manager)
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # AWS
    S3_BUCKET_NAME: str = ""  # loaded from secrets manager
    AWS_REGION: str = "us-east-1"

    # Stripe (loaded from secrets manager)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PREMIUM_PRICE_ID: str = ""

    # App config
    MAX_IMAGE_SIZE_MB: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def is_prod(self) -> bool:
        return self.ENV == Environment.PROD

    @property
    def FRONTEND_URL(self) -> str:
        if self.is_prod:
            return "https://norwood-ai.com"
        return "http://localhost:8000"

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        if self.is_prod:
            return ["https://norwood-ai.com", "http://norwood-ai.com"]
        return ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"]

    @property
    def STRIPE_SUCCESS_URL(self) -> str:
        """Dynamic Stripe success URL based on environment."""
        return f"{self.FRONTEND_URL}/checkout/success"

    @property
    def STRIPE_CANCEL_URL(self) -> str:
        """Dynamic Stripe cancel URL based on environment."""
        return f"{self.FRONTEND_URL}/checkout/cancel"

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    def require_anthropic_key(self) -> str:
        """Get API key or raise an error."""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return self.ANTHROPIC_API_KEY


def _create_settings() -> Settings:
    """
    Create application settings.

    Secrets are loaded from AWS Secrets Manager and override
    any values from environment variables.
    """
    # First, load base settings from env
    settings = Settings()

    # Load secrets from AWS Secrets Manager
    aws_secrets = _load_secrets_from_aws(settings.AWS_REGION)

    if aws_secrets:
        # Create new settings with AWS secrets overlaid
        settings = Settings(**aws_secrets)

    return settings


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return _create_settings()
