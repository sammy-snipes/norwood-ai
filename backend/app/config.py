import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ANTHROPIC_API_KEY: str = ""
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Celery / Redis
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    class Config:
        env_file = "backend/.env"
        extra = "ignore"

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    def require_anthropic_key(self) -> str:
        """Get API key or raise an error."""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return self.ANTHROPIC_API_KEY


settings = Settings()
