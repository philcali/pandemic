"""Tests for source management."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pandemic_core.sources import (
    GitHubSourceHandler,
    HttpSourceHandler,
    LocalSourceHandler,
    SourceManager,
)


class TestGitHubSourceHandler:
    """Test GitHub source handler."""

    def test_validate_source(self, test_config):
        """Test GitHub source validation."""
        handler = GitHubSourceHandler(test_config)

        assert handler.validate_source("github://user/repo")
        assert handler.validate_source("github://user/repo@v1.0.0")
        assert not handler.validate_source("https://github.com/user/repo")
        assert not handler.validate_source("file:///path/to/file")

    @pytest.mark.asyncio
    async def test_download(self, test_config, temp_dir):
        """Test GitHub download."""
        handler = GitHubSourceHandler(test_config)

        with (
            patch.object(handler, "_download_file", new_callable=AsyncMock),
            patch.object(handler, "_extract_archive", new_callable=AsyncMock),
        ):
            result = await handler.download("github://user/repo@v1.0.0", temp_dir)

            assert result["source"] == "github://user/repo@v1.0.0"
            assert result["type"] == "github"
            assert result["repository"] == "user/repo"
            assert result["ref"] == "v1.0.0"


class TestHttpSourceHandler:
    """Test HTTP source handler."""

    def test_validate_source(self, test_config):
        """Test HTTP source validation."""
        handler = HttpSourceHandler(test_config)

        assert handler.validate_source("http://example.com/file.tar.gz")
        assert handler.validate_source("https://example.com/file.tar.gz")
        assert not handler.validate_source("github://user/repo")
        assert not handler.validate_source("file:///path/to/file")

    @pytest.mark.asyncio
    async def test_download_archive(self, test_config, temp_dir):
        """Test HTTP archive download."""
        handler = HttpSourceHandler(test_config)

        with (
            patch.object(handler, "_download_file", new_callable=AsyncMock),
            patch.object(handler, "_extract_archive", new_callable=AsyncMock),
        ):
            result = await handler.download("https://example.com/infection.tar.gz", temp_dir)

            assert result["source"] == "https://example.com/infection.tar.gz"
            assert result["type"] == "http"
            assert result["filename"] == "infection.tar.gz"

    @pytest.mark.asyncio
    async def test_download_single_file(self, test_config, temp_dir):
        """Test HTTP single file download."""
        handler = HttpSourceHandler(test_config)

        with patch.object(handler, "_download_file", new_callable=AsyncMock):
            result = await handler.download("https://example.com/script.py", temp_dir)

            assert result["source"] == "https://example.com/script.py"
            assert result["type"] == "http"
            assert result["filename"] == "script.py"


class TestLocalSourceHandler:
    """Test local source handler."""

    def test_validate_source(self, test_config):
        """Test local source validation."""
        handler = LocalSourceHandler(test_config)

        assert handler.validate_source("file:///path/to/file")
        assert handler.validate_source("/path/to/file")
        assert not handler.validate_source("github://user/repo")
        assert not handler.validate_source("https://example.com/file")

    @pytest.mark.asyncio
    async def test_download_file(self, test_config, temp_dir):
        """Test local file copy."""
        handler = LocalSourceHandler(test_config)

        # Create test file
        test_file = temp_dir / "source.txt"
        test_file.write_text("test content")

        target_dir = temp_dir / "target"
        result = await handler.download(str(test_file), target_dir)

        assert result["source"] == str(test_file)
        assert result["type"] == "local"
        assert result["isDirectory"] is False
        assert (target_dir / "source.txt").exists()

    @pytest.mark.asyncio
    async def test_download_directory(self, test_config, temp_dir):
        """Test local directory copy."""
        handler = LocalSourceHandler(test_config)

        # Create test directory
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        target_dir = temp_dir / "target"
        result = await handler.download(str(source_dir), target_dir)

        assert result["source"] == str(source_dir)
        assert result["type"] == "local"
        assert result["isDirectory"] is True
        assert (target_dir / "file1.txt").exists()
        assert (target_dir / "file2.txt").exists()


class TestSourceManager:
    """Test source manager."""

    def test_get_handler(self, test_config):
        """Test handler selection."""
        manager = SourceManager(test_config)

        github_handler = manager._get_handler("github://user/repo")
        assert isinstance(github_handler, GitHubSourceHandler)

        http_handler = manager._get_handler("https://example.com/file")
        assert isinstance(http_handler, HttpSourceHandler)

        local_handler = manager._get_handler("/path/to/file")
        assert isinstance(local_handler, LocalSourceHandler)

        unknown_handler = manager._get_handler("unknown://source")
        assert unknown_handler is None

    @pytest.mark.asyncio
    async def test_install_from_source(self, test_config, temp_dir):
        """Test complete installation from source."""
        test_config.infections_dir = str(temp_dir)
        manager = SourceManager(test_config)

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.validate_source.return_value = True
        mock_handler.download = AsyncMock(
            return_value={
                "source": "test://source",
                "type": "test",
            }
        )

        manager.handlers = [mock_handler]

        with patch.object(
            manager, "_load_infection_config", new_callable=AsyncMock
        ) as mock_load_config:
            mock_load_config.return_value = {"metadata": {"name": "test"}}

            result = await manager.install_from_source("test://source", "test-infection")

            assert "installationPath" in result
            assert "downloadInfo" in result
            assert "configInfo" in result
            mock_handler.download.assert_called_once()

    def test_validate_source_security_allowed(self, test_config):
        """Test source security validation with allowed sources."""
        test_config.allowed_sources = ["github://trusted/", "https://trusted.com/"]
        manager = SourceManager(test_config)

        # Should not raise
        manager._validate_source_security("github://trusted/repo")
        manager._validate_source_security("https://trusted.com/file")

    def test_validate_source_security_blocked(self, test_config):
        """Test source security validation with blocked sources."""
        test_config.allowed_sources = ["github://trusted/"]
        manager = SourceManager(test_config)

        with pytest.raises(Exception):  # SecurityError
            manager._validate_source_security("github://untrusted/repo")

    @pytest.mark.asyncio
    async def test_load_infection_config_exists(self, test_config, temp_dir):
        """Test loading existing infection config."""
        manager = SourceManager(test_config)

        # Create config file
        config_file = temp_dir / "infection.yaml"
        config_file.write_text(
            """
metadata:
  name: test-infection
  version: 1.0.0
execution:
  command: ./bin/test
"""
        )

        config = await manager._load_infection_config(temp_dir)

        assert config["metadata"]["name"] == "test-infection"
        assert config["metadata"]["version"] == "1.0.0"
        assert config["execution"]["command"] == "./bin/test"

    @pytest.mark.asyncio
    async def test_load_infection_config_missing(self, test_config, temp_dir):
        """Test loading missing infection config creates default."""
        manager = SourceManager(test_config)

        config = await manager._load_infection_config(temp_dir)

        assert config["metadata"]["name"] == temp_dir.name
        assert config["metadata"]["version"] == "unknown"
        assert "execution" in config
