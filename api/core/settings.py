from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Tuple

from dotenv import load_dotenv


def _load_env_files() -> None:
    """Load environment variables from common project-level locations."""

    root = Path(__file__).resolve().parents[2]
    candidates: Iterable[Path] = (
        root / ".env.local",
        root / ".env",
        root / "api" / ".env.local",
    )

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(dotenv_path=candidate, override=False)


_load_env_files()


def _parse_origins() -> Tuple[str, ...]:
    raw = os.getenv("CORS_ALLOW_ORIGINS")
    if not raw:
        return ("*",)

    values = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    return values or ("*",)


def _parse_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Central FastAPI configuration derived from environment variables."""

    title: str = field(default="Website Insights API")
    description: str = field(default="AI-powered website analysis and conversational insights")
    version: str = field(default="1.0.0")
    secret_key: str = field(default_factory=lambda: os.getenv("API_SECRET_KEY", "your-secret-key-here"))
    cors_allow_origins: Tuple[str, ...] = field(default_factory=_parse_origins)
    browser_question_limit: int = field(default_factory=lambda: _parse_int("GROQ_BROWSER_QUESTION_LIMIT", 3))
    rate_limit_analyze: str = field(default_factory=lambda: os.getenv("RATE_LIMIT_ANALYZE", "10/minute"))
    rate_limit_chat: str = field(default_factory=lambda: os.getenv("RATE_LIMIT_CHAT", "20/minute"))
    deepinfra_api_key: str = field(default_factory=lambda: os.getenv("DEEPINFRA_API_KEY", "di-YOUR_DEEPINFRA_API_KEY_HERE"))


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance for dependency injection."""

    return Settings()
