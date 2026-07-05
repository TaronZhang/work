"""Bearer Token authentication for external API endpoints."""

from __future__ import annotations

import hmac
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_scheme = HTTPBearer(auto_error=False)


def generate_api_token() -> str:
    """Generate a cryptographically random API token (43 chars, 256 bits)."""
    return secrets.token_urlsafe(32)


async def verify_bearer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> None:
    """FastAPI dependency: require a valid Bearer token in the Authorization header.

    The expected token is read from settings.api_auth_token.

    Usage:
        @router.get("/api/external/tasks")
        async def tasks(_: None = Depends(verify_bearer)):
            ...
    """
    from app.config import settings

    expected = settings.api_auth_token

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API auth token not configured. Please generate a token in Settings.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
