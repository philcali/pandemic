"""Tests for cloud provider implementations."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pandemic_iam.providers import AWSProvider, Credentials


class TestAWSProvider:
    """Test AWS provider implementation."""

    @pytest.fixture
    def aws_config(self):
        """AWS provider configuration."""
        return {
            "region": "us-east-1",
            "trust_anchor_arn": "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-123",
            "profile_arn": "arn:aws:rolesanywhere:us-east-1:123456789012:profile/profile-123",
            "role_arn": "arn:aws:iam::123456789012:role/PandemicRole",
        }

    @pytest.fixture
    def test_certificate(self):
        """Generate test certificate and private key."""
        # Generate private key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Pandemic Test"),
                x509.NameAttribute(NameOID.COMMON_NAME, "test.pandemic.local"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=365))
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        return cert, private_key

    def test_provider_initialization(self, aws_config):
        """Test AWS provider initialization."""
        provider = AWSProvider(aws_config)

        assert provider.region == "us-east-1"
        assert provider.trust_anchor_arn == aws_config["trust_anchor_arn"]
        assert provider.profile_arn == aws_config["profile_arn"]

    def test_provider_initialization_missing_config(self):
        """Test AWS provider initialization with missing config."""
        with pytest.raises(ValueError, match="requires trust_anchor_arn"):
            AWSProvider({"region": "us-east-1"})

    def test_validate_certificate_valid(self, aws_config, test_certificate):
        """Test certificate validation with valid certificate."""
        cert, private_key = test_certificate
        provider = AWSProvider(aws_config)

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            f.write(cert_pem)
            cert_path = Path(f.name)

        try:
            # Set secure permissions
            cert_path.chmod(0o600)

            assert provider.validate_certificate(cert_path) is True
        finally:
            cert_path.unlink()

    def test_validate_certificate_insecure_permissions(self, aws_config, test_certificate):
        """Test certificate validation with insecure permissions."""
        cert, private_key = test_certificate
        provider = AWSProvider(aws_config)

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            f.write(cert_pem)
            cert_path = Path(f.name)

        try:
            # Set insecure permissions
            cert_path.chmod(0o644)

            assert provider.validate_certificate(cert_path) is False
        finally:
            cert_path.unlink()

    def test_validate_certificate_nonexistent(self, aws_config):
        """Test certificate validation with nonexistent file."""
        provider = AWSProvider(aws_config)

        assert provider.validate_certificate(Path("/nonexistent/cert.pem")) is False

    @pytest.mark.asyncio
    async def test_exchange_certificate_mock(self, aws_config, test_certificate):
        """Test certificate exchange with mock response."""
        cert, private_key = test_certificate
        provider = AWSProvider(aws_config)

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as cert_file:
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            cert_file.write(cert_pem)
            cert_path = Path(cert_file.name)

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as key_file:
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            key_file.write(key_pem)
            key_path = Path(key_file.name)

        try:
            # Set secure permissions
            cert_path.chmod(0o600)
            key_path.chmod(0o600)

            # Mock the create_session method to return test credentials
            with patch.object(provider, "_create_session", new_callable=AsyncMock) as mock_session:
                mock_session.return_value = provider._create_mock_response(3600)

                credentials = await provider.exchange_certificate(cert_path, key_path, 3600)

                assert isinstance(credentials, Credentials)
                assert credentials.access_key_id.startswith("ASIA")
                assert credentials.secret_access_key.startswith("mock-secret-key")
                assert credentials.session_token.startswith("mock-session-token")
                assert credentials.region == "us-east-1"

        finally:
            cert_path.unlink()
            key_path.unlink()


class TestCredentials:
    """Test Credentials class."""

    def test_credentials_creation(self):
        """Test credentials creation."""
        creds = Credentials(
            access_key_id="AKIATEST",
            secret_access_key="secret123",
            session_token="token123",
            region="us-west-2",
        )

        assert creds.access_key_id == "AKIATEST"
        assert creds.secret_access_key == "secret123"
        assert creds.session_token == "token123"
        assert creds.region == "us-west-2"

    def test_credentials_to_dict(self):
        """Test credentials dictionary conversion."""
        from datetime import datetime

        expiration = datetime.utcnow()
        creds = Credentials(
            access_key_id="AKIATEST",
            secret_access_key="secret123",
            session_token="token123",
            expiration=expiration,
            region="us-west-2",
        )

        result = creds.to_dict()

        assert result["accessKeyId"] == "AKIATEST"
        assert result["secretAccessKey"] == "secret123"
        assert result["sessionToken"] == "token123"
        assert result["region"] == "us-west-2"
        assert result["expiration"] == expiration.isoformat() + "Z"

    def test_credentials_is_expired(self):
        """Test credentials expiration check."""
        from datetime import datetime, timedelta

        # Not expired
        future_expiration = datetime.utcnow() + timedelta(hours=1)
        creds = Credentials(
            access_key_id="AKIATEST", secret_access_key="secret123", expiration=future_expiration
        )
        assert not creds.is_expired()

        # Expired
        past_expiration = datetime.utcnow() - timedelta(hours=1)
        creds.expiration = past_expiration
        assert creds.is_expired()

        # No expiration
        creds.expiration = None
        assert not creds.is_expired()
