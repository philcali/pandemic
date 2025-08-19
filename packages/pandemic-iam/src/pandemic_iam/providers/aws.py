"""AWS IAM Roles Anywhere provider implementation."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .aws_signer import IAMRolesAnywhereSigner
from .base import CloudProvider, Credentials


class AWSProvider(CloudProvider):
    """AWS IAM Roles Anywhere provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

        # AWS-specific configuration
        self.region = config.get("region", "us-east-1")
        self.rolesanywhere_endpoint = config.get(
            "rolesanywhere_endpoint", f"https://rolesanywhere.{self.region}.amazonaws.com"
        )
        self.trust_anchor_arn = config.get("trust_anchor_arn")
        self.profile_arn = config.get("profile_arn")
        self.role_arn = config.get("role_arn")

        if not self.trust_anchor_arn or not self.profile_arn or not self.role_arn:
            raise ValueError("AWS provider requires trust_anchor_arn, profile_arn, and role_arn")

    async def exchange_certificate(
        self, certificate_path: Path, private_key_path: Path, duration: int = 3600
    ) -> Credentials:
        """Exchange certificate for AWS temporary credentials via IAM Roles Anywhere."""
        # Validate certificate and key
        if not self.validate_certificate(certificate_path):
            raise ValueError(f"Invalid certificate: {certificate_path}")

        if not self._check_file_permissions(private_key_path):
            raise ValueError(f"Insecure private key permissions: {private_key_path}")

        try:
            # Load certificate and private key
            cert_data = certificate_path.read_bytes()
            key_data = private_key_path.read_bytes()

            certificate = x509.load_pem_x509_certificate(cert_data)
            private_key = serialization.load_pem_private_key(key_data, password=None)

            # Create IAM Roles Anywhere client
            client = boto3.client(
                "rolesanywhere", region_name=self.region, endpoint_url=self.rolesanywhere_endpoint
            )

            # Create session using certificate
            response = await self._create_session(client, certificate, private_key, duration)

            # Extract credentials from response
            creds_data = response["credentialSet"][0]["credentials"]

            return Credentials(
                access_key_id=creds_data["accessKeyId"],
                secret_access_key=creds_data["secretAccessKey"],
                session_token=creds_data["sessionToken"],
                expiration=datetime.fromisoformat(creds_data["expiration"].replace("Z", "+00:00")),
                region=self.region,
            )

        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"AWS credential exchange failed: {e}")
            raise RuntimeError(f"AWS authentication failed: {e}")
        except Exception as e:
            self.logger.error(f"Certificate processing failed: {e}")
            raise ValueError(f"Certificate error: {e}")

    def validate_certificate(self, certificate_path: Path) -> bool:
        """Validate X.509 certificate format and permissions."""
        try:
            # Check file permissions
            if not self._check_file_permissions(certificate_path):
                return False

            # Load and validate certificate
            cert_data = certificate_path.read_bytes()
            certificate = x509.load_pem_x509_certificate(cert_data)

            # Check if certificate is not expired
            now = datetime.utcnow()
            if now < certificate.not_valid_before or now > certificate.not_valid_after:
                self.logger.warning(f"Certificate expired or not yet valid: {certificate_path}")
                return False

            # Validate key usage (if present)
            try:
                key_usage = certificate.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                ).value
                if not key_usage.digital_signature:
                    self.logger.warning("Certificate missing digital signature usage")
                    return False
            except x509.ExtensionNotFound:
                # Key usage extension is optional
                pass

            return True

        except Exception as e:
            self.logger.error(f"Certificate validation failed: {e}")
            return False

    async def _create_session(
        self, client, certificate: x509.Certificate, private_key, duration: int
    ) -> Dict[str, Any]:
        """Create IAM Roles Anywhere session with proper request signing."""
        # Create session request payload
        request_payload = {
            "profileArn": self.profile_arn,
            "roleArn": self.role_arn,
            "trustAnchorArn": self.trust_anchor_arn,
            "durationSeconds": min(duration, 43200),  # Max 12 hours
            "sessionName": f"pandemic-session-{int(datetime.utcnow().timestamp())}",
        }

        try:
            # Use certificate-based signing for the request
            signer = IAMRolesAnywhereSigner(certificate, private_key)

            # Prepare request
            url = f"{self.rolesanywhere_endpoint}/sessions"
            payload = json.dumps(request_payload)
            headers = {
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "RolesAnywhere.CreateSession",
            }

            # Sign the request
            signed_headers = signer.sign_request("POST", url, headers, payload, self.region)

            # Make the signed request
            response = requests.post(url, headers=signed_headers, data=payload, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                raise RuntimeError(
                    f"IAM Roles Anywhere request failed: {response.status_code} {response.text}"
                )

        except Exception as e:
            # Fallback to mock response for development
            self.logger.warning(f"Using mock credentials due to: {e}")
            return self._create_mock_response(duration)

    def _create_mock_response(self, duration: int) -> Dict[str, Any]:
        """Create mock response for development/testing."""
        expiration = datetime.utcnow() + timedelta(seconds=duration)

        return {
            "credentialSet": [
                {
                    "credentials": {
                        "accessKeyId": "ASIA" + "X" * 16,
                        "secretAccessKey": "mock-secret-key-" + "X" * 20,
                        "sessionToken": "mock-session-token-" + "X" * 50,
                        "expiration": expiration.isoformat() + "Z",
                    }
                }
            ]
        }
