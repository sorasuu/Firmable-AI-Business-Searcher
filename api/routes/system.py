from __future__ import annotations

from fastapi import APIRouter, Depends

from api.core.settings import Settings
from api.dependencies import get_settings_dependency

router = APIRouter(tags=["system"])


@router.get("/")
def read_root(settings: Settings = Depends(get_settings_dependency)) -> dict[str, str | dict[str, str]]:
    return {
        "message": settings.title,
        "version": settings.version,
        "endpoints": {
            "analyze": "/api/analyze",
            "chat": "/api/chat",
        },
    }


@router.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/health")
def legacy_health_check() -> dict[str, str]:
    return {"status": "healthy"}
