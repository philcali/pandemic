"""Authentication middleware and utilities."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .models.auth import TokenPayload, UserInfo
from .users import User, UserProvider


class AuthManager:
    """Manages authentication and JWT tokens."""

    def __init__(self, jwt_secret: str, jwt_expiry: int, user_provider: UserProvider):
        self.jwt_secret = jwt_secret
        self.jwt_expiry = jwt_expiry
        self.user_provider = user_provider
        self.logger = logging.getLogger(__name__)
        self.security = HTTPBearer()

    def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        now = datetime.utcnow()
        payload = TokenPayload(
            sub=user.username,
            exp=int((now + timedelta(seconds=self.jwt_expiry)).timestamp()),
            iat=int(now.timestamp()),
            roles=user.roles,
        )

        return jwt.encode(payload.model_dump(), self.jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return TokenPayload(**payload)
        except JWTError as e:
            self.logger.warning(f"JWT verification failed: {e}")
            return None

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> UserInfo:
        """Get current authenticated user from JWT token."""
        token_payload = self.verify_token(credentials.credentials)

        if not token_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if token is expired
        if datetime.utcnow().timestamp() > token_payload.exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user info
        user = await self.user_provider.get_user(token_payload.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserInfo(
            username=user.username, email=user.email, full_name=user.full_name, roles=user.roles
        )

    def require_roles(self, required_roles: List[str]):
        """Dependency to require specific roles."""

        async def check_roles(current_user: UserInfo = Depends(self.get_current_user)):
            if not any(role in current_user.roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
                )
            return current_user

        return check_roles
