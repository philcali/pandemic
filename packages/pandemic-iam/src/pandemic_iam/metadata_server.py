"""IMDSv2-style metadata server for cloud credentials."""

import asyncio
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from .manager import IAMManager


class MetadataServer:
    """IMDSv2-style metadata server for cloud credentials."""

    def __init__(self, iam_manager: IAMManager, config: Dict):
        self.iam_manager = iam_manager
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Token storage (in production, use Redis or similar)
        self.tokens: Dict[str, Dict] = {}

        # Credential cache
        self.credential_cache: Dict[str, Dict] = {}

        # Create FastAPI app
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(
            title="Pandemic IAM Metadata Service",
            description="IMDSv2-style metadata service for cloud credentials",
            version="1.0.0",
            docs_url=None,  # Disable docs for security
            redoc_url=None,
        )

        @app.put("/latest/api/token", response_class=PlainTextResponse)
        async def get_token(
            request: Request,
            x_pandemic_token_ttl_seconds: int = Header(21600, alias="X-pandemic-token-ttl-seconds"),
        ):
            """Get session token (IMDSv2 style)."""
            # Validate TTL
            if x_pandemic_token_ttl_seconds < 1 or x_pandemic_token_ttl_seconds > 21600:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token TTL must be between 1 and 21600 seconds",
                )

            # Generate secure token
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(seconds=x_pandemic_token_ttl_seconds)

            # Store token
            self.tokens[token] = {
                "expiry": expiry,
                "client_ip": request.client.host,
                "created_at": datetime.utcnow(),
            }

            self.logger.info(f"Generated token for {request.client.host}, expires at {expiry}")
            return token

        @app.get("/latest/meta-data/iam/security-credentials/", response_class=PlainTextResponse)
        async def list_providers(x_pandemic_token: str = Header(..., alias="X-pandemic-token")):
            """List available credential providers."""
            self._validate_token(x_pandemic_token)

            providers = list(self.iam_manager.providers.keys())
            return "\n".join(providers)

        @app.get("/latest/meta-data/iam/security-credentials/{provider}")
        async def get_credentials(
            provider: str, x_pandemic_token: str = Header(..., alias="X-pandemic-token")
        ):
            """Get credentials for specific provider."""
            self._validate_token(x_pandemic_token)

            if provider not in self.iam_manager.providers:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider not found: {provider}"
                )

            try:
                # Check cache first
                cache_key = f"{provider}_credentials"
                cached = self.credential_cache.get(cache_key)

                if cached and not self._is_credential_expired(cached):
                    self.logger.debug(f"Returning cached credentials for {provider}")
                    return cached["response"]

                # Get fresh credentials
                credentials = await self._get_provider_credentials(provider)

                # Format response based on provider
                if provider == "aws":
                    response = {
                        "Code": "Success",
                        "LastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "Type": "AWS-HMAC",
                        "AccessKeyId": credentials.access_key_id,
                        "SecretAccessKey": credentials.secret_access_key,
                        "Token": credentials.session_token,
                        "Expiration": (
                            credentials.expiration.strftime("%Y-%m-%dT%H:%M:%SZ")
                            if credentials.expiration
                            else None
                        ),
                    }
                elif provider == "azure":
                    response = {
                        "Code": "Success",
                        "LastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "Type": "Azure-Bearer",
                        "AccessToken": credentials.access_key_id,  # Azure uses access_token
                        "Expiration": (
                            credentials.expiration.strftime("%Y-%m-%dT%H:%M:%SZ")
                            if credentials.expiration
                            else None
                        ),
                    }
                else:
                    # Generic format
                    response = credentials.to_dict()
                    response["Code"] = "Success"
                    response["LastUpdated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

                # Cache credentials
                self.credential_cache[cache_key] = {
                    "response": response,
                    "expiration": credentials.expiration,
                    "cached_at": datetime.utcnow(),
                }

                self.logger.info(f"Provided fresh credentials for {provider}")
                return response

            except Exception as e:
                self.logger.error(f"Failed to get credentials for {provider}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to retrieve credentials: {str(e)}",
                )

        @app.get("/latest/meta-data/instance-id", response_class=PlainTextResponse)
        async def get_instance_id(x_pandemic_token: str = Header(..., alias="X-pandemic-token")):
            """Get pandemic instance ID."""
            self._validate_token(x_pandemic_token)
            return "pandemic-" + secrets.token_hex(8)

        return app

    def _validate_token(self, token: str):
        """Validate session token."""
        if not token or token not in self.tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing token"
            )

        token_data = self.tokens[token]
        if datetime.utcnow() > token_data["expiry"]:
            # Clean up expired token
            del self.tokens[token]
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    def _is_credential_expired(self, cached_creds: Dict) -> bool:
        """Check if cached credentials are expired."""
        if not cached_creds.get("expiration"):
            return False

        # Refresh 5 minutes before expiration
        refresh_time = cached_creds["expiration"] - timedelta(minutes=5)
        return datetime.utcnow() >= refresh_time

    async def _get_provider_credentials(self, provider: str):
        """Get credentials from provider."""
        provider_config = self.config.get("providers", {}).get(provider, {})
        cert_config = self.config.get("certificates", {})

        cert_path = cert_config.get("default_cert", f"/etc/pandemic/certs/{provider}.pem")
        key_path = cert_config.get("default_key", f"/etc/pandemic/certs/{provider}.key")

        return await self.iam_manager.get_credentials(
            provider=provider, certificate_path=cert_path, private_key_path=key_path
        )

    async def cleanup_expired_tokens(self):
        """Background task to clean up expired tokens."""
        while True:
            try:
                now = datetime.utcnow()
                expired_tokens = [
                    token for token, data in self.tokens.items() if now > data["expiry"]
                ]

                for token in expired_tokens:
                    del self.tokens[token]

                if expired_tokens:
                    self.logger.debug(f"Cleaned up {len(expired_tokens)} expired tokens")

                # Sleep for 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"Error in token cleanup: {e}")
                await asyncio.sleep(60)
