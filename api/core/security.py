from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from .settings import Settings, get_settings


def verify_auth(
    authorization: str | None = Header(default=None, description="Bearer token for API access"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate the ``Authorization`` header using the shared application settings."""

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization format")

    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization token")
