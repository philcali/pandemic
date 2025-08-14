"""Common types and data models for Pandemic system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InfectionState(Enum):
    """Infection lifecycle states."""

    INSTALLING = "installing"
    INSTALLED = "installed"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    REMOVING = "removing"


class MessageType(Enum):
    """Message types for UDS communication."""

    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"


@dataclass
class InfectionMetadata:
    """Infection metadata."""

    name: str
    version: str
    description: str
    author: str


@dataclass
class InfectionSource:
    """Infection source configuration."""

    type: str  # github, http, local
    url: str
    ref: Optional[str] = None  # tag, branch, commit


@dataclass
class SystemdConfig:
    """Systemd service configuration."""

    user: str
    group: str
    working_directory: str
    environment: Dict[str, str]


@dataclass
class ExecutionConfig:
    """Execution configuration."""

    command: str
    restart: str = "always"
    restart_sec: int = 5


@dataclass
class ResourceLimits:
    """Resource limits configuration."""

    memory_limit: Optional[str] = None
    cpu_quota: Optional[str] = None


@dataclass
class InfectionConfig:
    """Complete infection configuration."""

    metadata: InfectionMetadata
    source: InfectionSource
    systemd: SystemdConfig
    execution: ExecutionConfig
    resources: ResourceLimits


@dataclass
class Message:
    """UDS message structure."""

    id: str
    type: MessageType
    command: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None
