from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core
    ENV: str = "dev"  # "dev" or "prod"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/norwood"

    # Redis / Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PREMIUM_PRICE_ID: str = ""

    # AWS S3
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"

    # App config
    MAX_IMAGE_SIZE_MB: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
