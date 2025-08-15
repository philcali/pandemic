"""Health and status route handlers."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import AuthManager
from ..client import PandemicClient
from ..models.auth import UserInfo
from ..models.infections import HealthResponse, StatusResponse

router = APIRouter(tags=["health"])


def create_health_router(auth_manager: AuthManager, client: PandemicClient) -> APIRouter:
    """Create health router with dependencies."""

    @router.get("/health", response_model=HealthResponse)
    async def health_check(
        infection_id: Optional[str] = Query(None, description="Check specific infection health")
    ):
        """Health check endpoint (no authentication required)."""
        try:
            result = await client.health_check(infection_id=infection_id)

            return HealthResponse(
                status=result["status"],
                daemon=result.get("daemon"),
                infection_id=result.get("infectionId"),
            )

        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    @router.get("/status", response_model=StatusResponse)
    async def get_status(
        infection_id: Optional[str] = Query(None, description="Get specific infection status"),
        current_user: UserInfo = Depends(auth_manager.get_current_user),
    ):
        """Get daemon or infection status."""
        try:
            result = await client.get_status(infection_id=infection_id)

            return StatusResponse(
                daemon=result.get("daemon"),
                infections=result.get("infections"),
                uptime=result.get("uptime"),
                infection_id=result.get("infectionId"),
                name=result.get("name"),
                state=result.get("state"),
                systemd_status=result.get("systemdStatus"),
            )

        except RuntimeError as e:
            if "not found" in str(e).lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router
