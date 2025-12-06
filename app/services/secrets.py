"""Service for fetching secrets from AWS Secrets Manager."""

import json
import logging
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# Secret names in AWS Secrets Manager
class SecretNames:
    GOOGLE_OAUTH = "google_oath"
    DB_HOSTNAME = "db_hostname"
    RDS_CREDENTIALS = "rds!db-772d01d0-2a2c-4a0a-b7c3-e24f1c38f0c1"
    S3_BUCKET = "s3_bucket_name"
    ANTHROPIC_API_KEY = "anthropic_api_key"
    JWT = "jwt"
    STRIPE = "stripe"


@dataclass
class GoogleOAuthCredentials:
    client_id: str
    client_secret: str


@dataclass
class StripeCredentials:
    secret_key: str
    publishable_key: str
    webhook_secret: str
    premium_price_id: str
    success_url: str
    cancel_url: str


@dataclass
class DatabaseCredentials:
    username: str
    password: str
    hostname: str
    port: int = 5432
    database: str = "postgres"

    @property
    def url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql://{self.username}:{self.password}@{self.hostname}:{self.port}/{self.database}"


@dataclass
class AppSecrets:
    """All application secrets loaded from AWS Secrets Manager."""

    google_oauth: GoogleOAuthCredentials | None = None
    database: DatabaseCredentials | None = None
    s3_bucket_name: str | None = None
    anthropic_api_key: str | None = None
    jwt_secret_key: str | None = None
    stripe: StripeCredentials | None = None


class SecretsManagerService:
    """Service for fetching secrets from AWS Secrets Manager."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._client = None
        self._cache: dict[str, dict | str] = {}

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("secretsmanager", region_name=self.region)
        return self._client

    def _get_raw_secret(self, secret_name: str) -> dict | str:
        """Fetch a raw secret value from AWS Secrets Manager."""
        if secret_name in self._cache:
            return self._cache[secret_name]

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response["SecretString"]

            # Try to parse as JSON, fall back to raw string
            try:
                value = json.loads(secret_string)
            except json.JSONDecodeError:
                value = secret_string

            self._cache[secret_name] = value
            logger.info(f"Fetched secret: {secret_name}")
            return value

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ResourceNotFoundException":
                logger.error(f"Secret not found: {secret_name}")
            elif error_code == "AccessDeniedException":
                logger.error(f"Access denied to secret: {secret_name}")
            else:
                logger.error(f"Failed to fetch secret {secret_name}: {e}")
            raise

    def _extract_string(self, secret: dict | str, *keys: str) -> str:
        """Extract a string value from a secret (handles both string and dict)."""
        if isinstance(secret, str):
            return secret
        if isinstance(secret, dict):
            for key in keys:
                if key in secret:
                    return secret[key]
        return str(secret)

    def get_google_oauth(self) -> GoogleOAuthCredentials:
        """Get Google OAuth credentials."""
        secret = self._get_raw_secret(SecretNames.GOOGLE_OAUTH)
        if not isinstance(secret, dict):
            raise ValueError(f"Expected JSON secret for {SecretNames.GOOGLE_OAUTH}")
        return GoogleOAuthCredentials(
            client_id=secret["google_client_id"],
            client_secret=secret["google_client_secret"],
        )

    def get_database_credentials(self) -> DatabaseCredentials:
        """Get full database credentials from RDS secret + hostname."""
        # Get hostname from separate secret
        hostname_secret = self._get_raw_secret(SecretNames.DB_HOSTNAME)
        hostname = self._extract_string(hostname_secret, "db_host", "hostname", "host")

        # Get username/password from RDS-managed secret
        rds_secret = self._get_raw_secret(SecretNames.RDS_CREDENTIALS)
        if not isinstance(rds_secret, dict):
            raise ValueError(f"Expected JSON secret for {SecretNames.RDS_CREDENTIALS}")

        return DatabaseCredentials(
            username=rds_secret["username"],
            password=rds_secret["password"],
            hostname=hostname,
        )

    def get_s3_bucket_name(self) -> str:
        """Get the S3 bucket name."""
        secret = self._get_raw_secret(SecretNames.S3_BUCKET)
        return self._extract_string(secret, "s3_bucket_name", "bucket_name", "name")

    def get_anthropic_api_key(self) -> str:
        """Get the Anthropic API key."""
        secret = self._get_raw_secret(SecretNames.ANTHROPIC_API_KEY)
        return self._extract_string(secret, "anthropic_api_key", "api_key", "key")

    def get_jwt_secret_key(self) -> str:
        """Get the JWT secret key."""
        secret = self._get_raw_secret(SecretNames.JWT)
        return self._extract_string(secret, "jwt", "jwt_secret", "secret")

    def get_stripe(self) -> StripeCredentials:
        """Get Stripe credentials."""
        secret = self._get_raw_secret(SecretNames.STRIPE)
        if not isinstance(secret, dict):
            raise ValueError(f"Expected JSON secret for {SecretNames.STRIPE}")
        return StripeCredentials(
            secret_key=secret.get("secret_key")
            or secret.get("secret_key "),  # note: has trailing space in AWS
            publishable_key=secret["publishable_key"],
            webhook_secret=secret["webhook_secret"],
            premium_price_id=secret["premium_price_id"],
            success_url=secret["success_url"],
            cancel_url=secret["cancel_url"],
        )

    def load_all(self) -> AppSecrets:
        """Load all application secrets."""
        secrets = AppSecrets()

        try:
            secrets.google_oauth = self.get_google_oauth()
        except Exception as e:
            logger.warning(f"Failed to load Google OAuth: {e}")

        try:
            secrets.database = self.get_database_credentials()
        except Exception as e:
            logger.warning(f"Failed to load database credentials: {e}")

        try:
            secrets.s3_bucket_name = self.get_s3_bucket_name()
        except Exception as e:
            logger.warning(f"Failed to load S3 bucket name: {e}")

        try:
            secrets.anthropic_api_key = self.get_anthropic_api_key()
        except Exception as e:
            logger.warning(f"Failed to load Anthropic API key: {e}")

        try:
            secrets.jwt_secret_key = self.get_jwt_secret_key()
        except Exception as e:
            logger.warning(f"Failed to load JWT secret key: {e}")

        try:
            secrets.stripe = self.get_stripe()
        except Exception as e:
            logger.warning(f"Failed to load Stripe credentials: {e}")

        return secrets

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()


# Singleton
_service: SecretsManagerService | None = None


def get_secrets_service(region: str = "us-east-1") -> SecretsManagerService:
    """Get or create the secrets manager service singleton."""
    global _service
    if _service is None:
        _service = SecretsManagerService(region=region)
    return _service
