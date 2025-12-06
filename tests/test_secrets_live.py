"""Live integration tests for secrets and connections.

These tests hit real AWS services and verify actual connectivity.
Run with: pytest tests/test_secrets_live.py -v
"""

import pytest

from app.services.secrets import (
    DatabaseCredentials,
    GoogleOAuthCredentials,
    SecretsManagerService,
    StripeCredentials,
)


@pytest.fixture(scope="module")
def secrets_service():
    """Create secrets service for live tests."""
    return SecretsManagerService(region="us-east-1")


@pytest.fixture(scope="module")
def all_secrets(secrets_service):
    """Load all secrets once for the module."""
    return secrets_service.load_all()


class TestSecretsRetrieval:
    """Test that all secrets can be retrieved from AWS."""

    def test_google_oauth_credentials(self, all_secrets):
        """Verify Google OAuth credentials are retrieved."""
        assert all_secrets.google_oauth is not None
        assert isinstance(all_secrets.google_oauth, GoogleOAuthCredentials)
        assert all_secrets.google_oauth.client_id
        assert all_secrets.google_oauth.client_secret
        assert "apps.googleusercontent.com" in all_secrets.google_oauth.client_id

    def test_database_credentials(self, all_secrets):
        """Verify database credentials are retrieved."""
        assert all_secrets.database is not None
        assert isinstance(all_secrets.database, DatabaseCredentials)
        assert all_secrets.database.username
        assert all_secrets.database.password
        assert all_secrets.database.hostname
        assert all_secrets.database.port == 5432

    def test_database_url_format(self, all_secrets):
        """Verify database URL is properly formatted."""
        url = all_secrets.database.url
        assert url.startswith("postgresql://")
        assert "@" in url
        assert ":5432/" in url

    def test_s3_bucket_name(self, all_secrets):
        """Verify S3 bucket name is retrieved."""
        assert all_secrets.s3_bucket_name is not None
        assert len(all_secrets.s3_bucket_name) > 0

    def test_anthropic_api_key(self, all_secrets):
        """Verify Anthropic API key is retrieved."""
        assert all_secrets.anthropic_api_key is not None
        assert len(all_secrets.anthropic_api_key) > 0

    def test_stripe_credentials(self, all_secrets):
        """Verify Stripe credentials are retrieved."""
        assert all_secrets.stripe is not None
        assert isinstance(all_secrets.stripe, StripeCredentials)
        assert all_secrets.stripe.secret_key
        assert all_secrets.stripe.publishable_key
        assert all_secrets.stripe.webhook_secret
        assert all_secrets.stripe.premium_price_id
        assert "sk_" in all_secrets.stripe.secret_key
        assert "pk_" in all_secrets.stripe.publishable_key

    def test_jwt_secret_key(self, all_secrets):
        """Verify JWT secret key is retrieved."""
        assert all_secrets.jwt_secret_key is not None
        assert len(all_secrets.jwt_secret_key) > 0


class TestDatabaseConnection:
    """Test actual database connectivity."""

    def test_can_connect_to_database(self, all_secrets):
        """Verify we can establish a database connection."""
        from sqlalchemy import create_engine, text

        engine = create_engine(all_secrets.database.url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_can_query_tables(self, all_secrets):
        """Verify we can query the database schema."""
        from sqlalchemy import create_engine, text

        engine = create_engine(all_secrets.database.url)

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            tables = [row[0] for row in result]
            assert len(tables) >= 0  # At least the query works


class TestS3Connection:
    """Test actual S3 connectivity."""

    def test_can_connect_to_s3(self, all_secrets):
        """Verify we can connect to S3 bucket."""
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")

        # Just verify we can access the bucket (list with max 1 item)
        response = s3.list_objects_v2(
            Bucket=all_secrets.s3_bucket_name,
            MaxKeys=1,
        )
        assert "Name" in response
        assert response["Name"] == all_secrets.s3_bucket_name


class TestAnthropicConnection:
    """Test actual Anthropic API connectivity."""

    def test_can_connect_to_anthropic(self, all_secrets):
        """Verify Anthropic API key works."""
        import anthropic

        client = anthropic.Anthropic(api_key=all_secrets.anthropic_api_key)

        # Just verify we can make a minimal API call
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'ok'"}],
        )
        assert response.content[0].text


class TestConfigIntegration:
    """Test that config properly loads from secrets."""

    def test_settings_loads_from_secrets(self):
        """Verify Settings object gets populated from AWS secrets."""
        from app.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.GOOGLE_CLIENT_ID
        assert settings.GOOGLE_CLIENT_SECRET
        assert settings.DATABASE_URL
        assert "postgresql://" in settings.DATABASE_URL
        assert settings.S3_BUCKET_NAME
        assert settings.ANTHROPIC_API_KEY
        assert settings.STRIPE_SECRET_KEY
        assert settings.STRIPE_PUBLISHABLE_KEY
        assert settings.STRIPE_WEBHOOK_SECRET
        assert settings.STRIPE_PREMIUM_PRICE_ID
        assert settings.JWT_SECRET_KEY

        get_settings.cache_clear()
