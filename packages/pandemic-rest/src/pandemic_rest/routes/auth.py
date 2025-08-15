"""Authentication route handlers."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import AuthManager
from ..models.auth import LoginRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["authentication"])


def create_auth_router(auth_manager: AuthManager) -> APIRouter:
    """Create authentication router with auth manager dependency."""

    @router.post("/login", response_model=TokenResponse)
    async def login(login_request: LoginRequest):
        """Authenticate user and return JWT token."""
        auth_result = await auth_manager.user_provider.authenticate(
            login_request.username, login_request.password
        )

        if not auth_result.success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_result.error or "Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create JWT token
        access_token = auth_manager.create_access_token(auth_result.user)

        return TokenResponse(access_token=access_token, expires_in=auth_manager.jwt_expiry)

    @router.get("/me", response_model=UserInfo)
    async def get_current_user_info(
        current_user: UserInfo = Depends(auth_manager.get_current_user),
    ):
        """Get current authenticated user information."""
        return current_user

    @router.post("/logout")
    async def logout():
        """Logout user (client should discard token)."""
        return {"message": "Successfully logged out"}

    return router
