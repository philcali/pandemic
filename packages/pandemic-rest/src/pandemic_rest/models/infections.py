"""Infection-related Pydantic models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class InstallRequest(BaseModel):
    """Install infection request model."""

    source: str
    name: Optional[str] = None
    config_overrides: Optional[Dict[str, Any]] = None


class InstallResponse(BaseModel):
    """Install infection response model."""

    infection_id: str
    service_name: str
    installation_path: str


class InfectionInfo(BaseModel):
    """Infection information model."""

    infection_id: str
    name: str
    state: str
    source: Optional[str] = None
    installation_path: Optional[str] = None
    service_name: Optional[str] = None
    systemd_status: Optional[Dict[str, Any]] = None


class InfectionList(BaseModel):
    """List of infections response model."""

    infections: List[InfectionInfo]
    total_count: int
    running_count: int


class ActionResponse(BaseModel):
    """Generic action response model."""

    status: str
    infection_id: str
    message: Optional[str] = None


class LogsResponse(BaseModel):
    """Logs response model."""

    infection_id: str
    logs: List[str]
    lines: int


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    daemon: Optional[bool] = None
    infection_id: Optional[str] = None


class StatusResponse(BaseModel):
    """Status response model."""

    daemon: Optional[str] = None
    infections: Optional[int] = None
    uptime: Optional[str] = None
    infection_id: Optional[str] = None
    name: Optional[str] = None
    state: Optional[str] = None
    systemd_status: Optional[Dict[str, Any]] = None
