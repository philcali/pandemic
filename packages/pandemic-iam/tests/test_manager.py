"""Tests for IAM manager."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pandemic_iam.manager import IAMManager
from pandemic_iam.providers import Credentials


class TestIAMManager:
    """Test IAM manager functionality."""

    @pytest.fixture
    def iam_config(self):
        """IAM manager configuration."""
        return {
            "providers": {
                "aws": {
                    "enabled": True,
                    "region": "us-east-1",
                    "trust_anchor_arn": "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-123",
                    "profile_arn": "arn:aws:rolesanywhere:us-east-1:123456789012:profile/profile-123",
                    "role_arn": "arn:aws:iam::123456789012:role/PandemicRole",
                },
                "azure": {"enabled": False},
            }
        }

    def test_manager_initialization(self, iam_config):
        """Test IAM manager initialization."""
        manager = IAMManager(iam_config)

        assert "aws" in manager.providers
        assert "azure" not in manager.providers
        assert len(manager.providers) == 1

    def test_manager_initialization_no_providers(self):
        """Test IAM manager with no enabled providers."""
        config = {"providers": {}}
        manager = IAMManager(config)

        assert len(manager.providers) == 0

    def test_list_providers(self, iam_config):
        """Test listing available providers."""
        manager = IAMManager(iam_config)
        providers = manager.list_providers()

        assert "aws" in providers
        assert providers["aws"]["enabled"] is True
        assert providers["aws"]["provider_class"] == "AWSProvider"
        assert "config" in providers["aws"]

    @pytest.mark.asyncio
    async def test_get_credentials_success(self, iam_config):
        """Test successful credential retrieval."""
        manager = IAMManager(iam_config)

        # Create temporary certificate and key files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as cert_file:
            cert_file.write("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----")
            cert_path = cert_file.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as key_file:
            key_file.write("-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----")
            key_path = key_file.name

        try:
            # Set secure permissions
            Path(cert_path).chmod(0o600)
            Path(key_path).chmod(0o600)

            # Mock the provider's exchange_certificate method
            mock_credentials = Credentials(
                access_key_id="AKIATEST",
                secret_access_key="secret123",
                session_token="token123",
                region="us-east-1",
            )

            with patch.object(
                manager.providers["aws"], "exchange_certificate", new_callable=AsyncMock
            ) as mock_exchange:
                mock_exchange.return_value = mock_credentials

                credentials = await manager.get_credentials(
                    provider="aws",
                    certificate_path=cert_path,
                    private_key_path=key_path,
                    duration=3600,
                )

                assert credentials.access_key_id == "AKIATEST"
                assert credentials.region == "us-east-1"
                mock_exchange.assert_called_once()

        finally:
            Path(cert_path).unlink()
            Path(key_path).unlink()

    @pytest.mark.asyncio
    async def test_get_credentials_invalid_provider(self, iam_config):
        """Test credential retrieval with invalid provider."""
        manager = IAMManager(iam_config)

        with pytest.raises(ValueError, match="Provider not available: invalid"):
            await manager.get_credentials(
                provider="invalid",
                certificate_path="/tmp/cert.pem",
                private_key_path="/tmp/key.pem",
            )

    @pytest.mark.asyncio
    async def test_get_credentials_missing_certificate(self, iam_config):
        """Test credential retrieval with missing certificate."""
        manager = IAMManager(iam_config)

        with pytest.raises(FileNotFoundError, match="Certificate not found"):
            await manager.get_credentials(
                provider="aws",
                certificate_path="/nonexistent/cert.pem",
                private_key_path="/nonexistent/key.pem",
            )

    def test_validate_certificate_success(self, iam_config):
        """Test certificate validation."""
        manager = IAMManager(iam_config)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as cert_file:
            cert_file.write("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----")
            cert_path = cert_file.name

        try:
            Path(cert_path).chmod(0o600)

            # Mock the provider's validate_certificate method
            with patch.object(manager.providers["aws"], "validate_certificate") as mock_validate:
                mock_validate.return_value = True

                result = manager.validate_certificate("aws", cert_path)

                assert result is True
                mock_validate.assert_called_once()

        finally:
            Path(cert_path).unlink()

    def test_validate_certificate_invalid_provider(self, iam_config):
        """Test certificate validation with invalid provider."""
        manager = IAMManager(iam_config)

        result = manager.validate_certificate("invalid", "/tmp/cert.pem")
        assert result is False

    def test_validate_certificate_missing_file(self, iam_config):
        """Test certificate validation with missing file."""
        manager = IAMManager(iam_config)

        result = manager.validate_certificate("aws", "/nonexistent/cert.pem")
        assert result is False
