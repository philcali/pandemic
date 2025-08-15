"""Installation source handlers for pandemic infections."""

import asyncio
import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .config import DaemonConfig


class SourceHandler(ABC):
    """Abstract base class for infection source handlers."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def download(self, source_url: str, target_dir: Path) -> Dict[str, Any]:
        """Download infection from source to target directory."""
        pass

    @abstractmethod
    def validate_source(self, source_url: str) -> bool:
        """Validate if this handler can process the given source URL."""
        pass


class GitHubSourceHandler(SourceHandler):
    """Handler for GitHub-based infection sources."""

    def validate_source(self, source_url: str) -> bool:
        """Validate GitHub source URL format."""
        return source_url.startswith("github://")

    async def download(self, source_url: str, target_dir: Path) -> Dict[str, Any]:
        """Download from GitHub repository."""
        # Parse github://user/repo@ref format
        url_part = source_url.replace("github://", "")
        if "@" in url_part:
            repo_path, ref = url_part.split("@", 1)
        else:
            repo_path, ref = url_part, "main"

        github_url = f"https://github.com/{repo_path}/archive/{ref}.tar.gz"

        self.logger.info(f"Downloading from GitHub: {github_url}")

        # Download and extract
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp_file:
            await self._download_file(github_url, tmp_file.name)
            await self._extract_archive(tmp_file.name, target_dir)

        return {
            "source": source_url,
            "type": "github",
            "repository": repo_path,
            "ref": ref,
            "downloadUrl": github_url,
        }

    async def _download_file(self, url: str, target_path: str):
        """Download file using curl."""
        process = await asyncio.create_subprocess_exec(
            "curl",
            "-L",
            "-o",
            target_path,
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Download failed: {stderr.decode()}")

    async def _extract_archive(self, archive_path: str, target_dir: Path):
        """Extract tar.gz archive."""
        target_dir.mkdir(parents=True, exist_ok=True)

        process = await asyncio.create_subprocess_exec(
            "tar",
            "-xzf",
            archive_path,
            "-C",
            str(target_dir),
            "--strip-components=1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Extraction failed: {stderr.decode()}")


class HttpSourceHandler(SourceHandler):
    """Handler for HTTP/HTTPS-based infection sources."""

    def validate_source(self, source_url: str) -> bool:
        """Validate HTTP source URL."""
        parsed = urlparse(source_url)
        return parsed.scheme in ("http", "https")

    async def download(self, source_url: str, target_dir: Path) -> Dict[str, Any]:
        """Download from HTTP URL."""
        parsed = urlparse(source_url)
        filename = Path(parsed.path).name or "infection.tar.gz"

        self.logger.info(f"Downloading from HTTP: {source_url}")

        target_dir.mkdir(parents=True, exist_ok=True)

        if filename.endswith((".tar.gz", ".tgz")):
            # Download and extract archive
            with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp_file:
                await self._download_file(source_url, tmp_file.name)
                await self._extract_archive(tmp_file.name, target_dir)
        else:
            # Download single file
            target_file = target_dir / filename
            await self._download_file(source_url, str(target_file))

        return {
            "source": source_url,
            "type": "http",
            "url": source_url,
            "filename": filename,
        }

    async def _download_file(self, url: str, target_path: str):
        """Download file using curl."""
        process = await asyncio.create_subprocess_exec(
            "curl",
            "-L",
            "-o",
            target_path,
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Download failed: {stderr.decode()}")

    async def _extract_archive(self, archive_path: str, target_dir: Path):
        """Extract tar.gz archive."""
        process = await asyncio.create_subprocess_exec(
            "tar",
            "-xzf",
            archive_path,
            "-C",
            str(target_dir),
            "--strip-components=1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Extraction failed: {stderr.decode()}")


class LocalSourceHandler(SourceHandler):
    """Handler for local filesystem-based infection sources."""

    def validate_source(self, source_url: str) -> bool:
        """Validate local source path."""
        return source_url.startswith("file://") or source_url.startswith("/")

    async def download(self, source_url: str, target_dir: Path) -> Dict[str, Any]:
        """Copy from local filesystem."""
        if source_url.startswith("file://"):
            source_path = Path(source_url.replace("file://", ""))
        else:
            source_path = Path(source_url)

        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        self.logger.info(f"Copying from local path: {source_path}")

        target_dir.mkdir(parents=True, exist_ok=True)

        if source_path.is_file():
            if source_path.suffix in (".tar.gz", ".tgz"):
                # Extract archive
                await self._extract_archive(str(source_path), target_dir)
            else:
                # Copy single file
                import shutil

                shutil.copy2(source_path, target_dir / source_path.name)
        else:
            # Copy directory contents
            import shutil

            for item in source_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_dir / item.name)
                else:
                    shutil.copytree(item, target_dir / item.name)

        return {
            "source": source_url,
            "type": "local",
            "path": str(source_path),
            "isDirectory": source_path.is_dir(),
        }

    async def _extract_archive(self, archive_path: str, target_dir: Path):
        """Extract tar.gz archive."""
        process = await asyncio.create_subprocess_exec(
            "tar",
            "-xzf",
            archive_path,
            "-C",
            str(target_dir),
            "--strip-components=1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Extraction failed: {stderr.decode()}")


class SourceManager:
    """Manages different infection source handlers."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.handlers = [
            GitHubSourceHandler(config),
            HttpSourceHandler(config),
            LocalSourceHandler(config),
        ]

    async def install_from_source(self, source_url: str, infection_name: str) -> Dict[str, Any]:
        """Install infection from source URL."""
        # Find appropriate handler
        handler = self._get_handler(source_url)
        if not handler:
            raise ValueError(f"No handler available for source: {source_url}")

        # Validate source if security is enabled
        if self.config.validate_signatures:
            self._validate_source_security(source_url)

        # Create target directory
        target_dir = Path(self.config.infections_dir) / infection_name
        if target_dir.exists():
            import shutil

            shutil.rmtree(target_dir)

        # Download and install
        download_info = await handler.download(source_url, target_dir)

        # Load infection configuration
        config_info = await self._load_infection_config(target_dir)

        return {
            "installationPath": str(target_dir),
            "downloadInfo": download_info,
            "configInfo": config_info,
        }

    def _get_handler(self, source_url: str) -> Optional[SourceHandler]:
        """Get appropriate handler for source URL."""
        for handler in self.handlers:
            if handler.validate_source(source_url):
                return handler
        return None

    def _validate_source_security(self, source_url: str):
        """Validate source against security policies."""
        if not self.config.allowed_sources:
            return  # No restrictions

        # Check if source matches allowed patterns
        for allowed in self.config.allowed_sources:
            if source_url.startswith(allowed):
                return

        raise SecurityError(f"Source not allowed: {source_url}")

    async def _load_infection_config(self, infection_dir: Path) -> Dict[str, Any]:
        """Load infection configuration from directory."""
        config_file = infection_dir / "infection.yaml"
        if not config_file.exists():
            # Create minimal config
            return {
                "metadata": {"name": infection_dir.name, "version": "unknown"},
                "execution": {"command": f"./bin/{infection_dir.name}"},
            }

        # Load YAML config
        import yaml

        with open(config_file) as f:
            config = yaml.safe_load(f)

        return config


class SecurityError(Exception):
    """Raised when source validation fails security checks."""

    pass
