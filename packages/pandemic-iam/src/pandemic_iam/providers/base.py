"""Abstract base class for cloud provider authentication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Credentials:
    """Cloud provider credentials."""

    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None
    expiration: Optional[datetime] = None
    region: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if credentials are expired."""
        if not self.expiration:
            return False
        return datetime.utcnow() >= self.expiration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "accessKeyId": self.access_key_id,
            "secretAccessKey": self.secret_access_key,
        }

        if self.session_token:
            result["sessionToken"] = self.session_token
        if self.expiration:
            result["expiration"] = self.expiration.isoformat() + "Z"
        if self.region:
            result["region"] = self.region

        return result


class CloudProvider(ABC):
    """Abstract base class for cloud provider authentication."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace("provider", "")

    @abstractmethod
    async def exchange_certificate(
        self, certificate_path: Path, private_key_path: Path, duration: int = 3600
    ) -> Credentials:
        """Exchange certificate for temporary credentials."""
        pass

    @abstractmethod
    def validate_certificate(self, certificate_path: Path) -> bool:
        """Validate certificate format and permissions."""
        pass

    def _check_file_permissions(self, file_path: Path) -> bool:
        """Check if file has secure permissions (600 or 400)."""
        if not file_path.exists():
            return False

        stat = file_path.stat()
        mode = stat.st_mode & 0o777

        # Allow 600 (rw-------) or 400 (r-------)
        return mode in (0o600, 0o400)
