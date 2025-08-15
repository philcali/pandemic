"""IAM Manager for coordinating cloud provider authentication."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .providers import AWSProvider, CloudProvider, Credentials


class IAMManager:
    """Manages cloud provider authentication and credential exchange."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.providers: Dict[str, CloudProvider] = {}

        # Initialize providers based on configuration
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize enabled cloud providers."""
        providers_config = self.config.get("providers", {})

        # Initialize AWS provider
        aws_config = providers_config.get("aws", {})
        if aws_config.get("enabled", False):
            try:
                self.providers["aws"] = AWSProvider(aws_config)
                self.logger.info("AWS provider initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize AWS provider: {e}")

        # TODO: Initialize Azure and GCP providers
        # azure_config = providers_config.get("azure", {})
        # gcp_config = providers_config.get("gcp", {})

        if not self.providers:
            self.logger.warning("No cloud providers enabled")

    async def get_credentials(
        self, provider: str, certificate_path: str, private_key_path: str, duration: int = 3600
    ) -> Credentials:
        """Get temporary credentials using certificate authentication."""
        if provider not in self.providers:
            raise ValueError(f"Provider not available: {provider}")

        cert_path = Path(certificate_path)
        key_path = Path(private_key_path)

        # Validate paths exist
        if not cert_path.exists():
            raise FileNotFoundError(f"Certificate not found: {certificate_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {private_key_path}")

        provider_instance = self.providers[provider]

        self.logger.info(f"Exchanging certificate for {provider} credentials")

        try:
            credentials = await provider_instance.exchange_certificate(
                cert_path, key_path, duration
            )

            self.logger.info(f"Successfully obtained {provider} credentials")
            return credentials

        except Exception as e:
            self.logger.error(f"Credential exchange failed for {provider}: {e}")
            raise

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """List available cloud providers and their status."""
        result = {}

        for name, provider in self.providers.items():
            result[name] = {
                "enabled": True,
                "provider_class": provider.__class__.__name__,
                "config": {
                    k: v
                    for k, v in provider.config.items()
                    if not k.endswith("_key") and not k.endswith("_secret")
                },
            }

        return result

    def validate_certificate(self, provider: str, certificate_path: str) -> bool:
        """Validate certificate for specific provider."""
        if provider not in self.providers:
            return False

        cert_path = Path(certificate_path)
        if not cert_path.exists():
            return False

        return self.providers[provider].validate_certificate(cert_path)
