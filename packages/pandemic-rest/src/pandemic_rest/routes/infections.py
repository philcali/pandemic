"""Infection management route handlers."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import AuthManager
from ..client import PandemicClient
from ..models.auth import UserInfo
from ..models.infections import (
    ActionResponse,
    HealthResponse,
    InfectionInfo,
    InfectionList,
    InstallRequest,
    InstallResponse,
    LogsResponse,
    StatusResponse,
)

router = APIRouter(prefix="/infections", tags=["infections"])


def create_infections_router(auth_manager: AuthManager, client: PandemicClient) -> APIRouter:
    """Create infections router with dependencies."""

    @router.get("", response_model=InfectionList)
    async def list_infections(
        state: Optional[str] = Query(None, description="Filter by infection state"),
        current_user: UserInfo = Depends(auth_manager.get_current_user),
    ):
        """List all infections."""
        try:
            result = await client.list_infections(filter_state=state)

            infections = [
                InfectionInfo(
                    infection_id=inf["infectionId"],
                    name=inf["name"],
                    state=inf["state"],
                    source=inf.get("source"),
                    installation_path=inf.get("installationPath"),
                    service_name=inf.get("serviceName"),
                )
                for inf in result["infections"]
            ]

            return InfectionList(
                infections=infections,
                total_count=result["totalCount"],
                running_count=result["runningCount"],
            )

        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("", response_model=InstallResponse)
    async def install_infection(
        install_request: InstallRequest,
        current_user: UserInfo = Depends(auth_manager.require_roles(["admin", "operator"])),
    ):
        """Install new infection."""
        try:
            result = await client.install_infection(
                source=install_request.source,
                name=install_request.name,
                config_overrides=install_request.config_overrides,
            )

            return InstallResponse(
                infection_id=result["infectionId"],
                service_name=result["serviceName"],
                installation_path=result["installationPath"],
            )

        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.get("/{infection_id}", response_model=InfectionInfo)
    async def get_infection(
        infection_id: str, current_user: UserInfo = Depends(auth_manager.get_current_user)
    ):
        """Get specific infection information."""
        try:
            result = await client.get_status(infection_id=infection_id)

            return InfectionInfo(
                infection_id=result["infectionId"],
                name=result["name"],
                state=result["state"],
                source=result.get("source"),
                installation_path=result.get("installationPath"),
                service_name=result.get("serviceName"),
                systemd_status=result.get("systemdStatus"),
            )

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.delete("/{infection_id}")
    async def remove_infection(
        infection_id: str,
        cleanup: bool = Query(True, description="Remove installation files"),
        current_user: UserInfo = Depends(auth_manager.require_roles(["admin", "operator"])),
    ):
        """Remove infection."""
        try:
            result = await client.remove_infection(infection_id, cleanup=cleanup)
            return {"message": "Infection removed successfully", **result}

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("/{infection_id}/start", response_model=ActionResponse)
    async def start_infection(
        infection_id: str,
        current_user: UserInfo = Depends(auth_manager.require_roles(["admin", "operator"])),
    ):
        """Start infection."""
        try:
            result = await client.start_infection(infection_id)
            return ActionResponse(
                status="started",
                infection_id=infection_id,
                message="Infection started successfully",
            )

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("/{infection_id}/stop", response_model=ActionResponse)
    async def stop_infection(
        infection_id: str,
        current_user: UserInfo = Depends(auth_manager.require_roles(["admin", "operator"])),
    ):
        """Stop infection."""
        try:
            result = await client.stop_infection(infection_id)
            return ActionResponse(
                status="stopped",
                infection_id=infection_id,
                message="Infection stopped successfully",
            )

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("/{infection_id}/restart", response_model=ActionResponse)
    async def restart_infection(
        infection_id: str,
        current_user: UserInfo = Depends(auth_manager.require_roles(["admin", "operator"])),
    ):
        """Restart infection."""
        try:
            result = await client.restart_infection(infection_id)
            return ActionResponse(
                status="restarted",
                infection_id=infection_id,
                message="Infection restarted successfully",
            )

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.get("/{infection_id}/logs", response_model=LogsResponse)
    async def get_infection_logs(
        infection_id: str,
        lines: int = Query(100, description="Number of log lines to retrieve"),
        current_user: UserInfo = Depends(auth_manager.get_current_user),
    ):
        """Get infection logs."""
        try:
            result = await client.get_logs(infection_id, lines=lines)

            return LogsResponse(infection_id=infection_id, logs=result.get("logs", []), lines=lines)

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router
