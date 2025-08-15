"""Authentication request/response models."""

from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """User information model."""

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[str] = []


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str  # username
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    roles: List[str] = []
