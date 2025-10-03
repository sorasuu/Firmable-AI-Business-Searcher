from __future__ import annotations

import importlib
from typing import Any, cast


def _load_attr(module: str, attribute: str) -> Any:
    try:
        return getattr(importlib.import_module(module), attribute)
    except ImportError as exc:  # pragma: no cover - fails fast on missing optional dep
        raise RuntimeError(
            "The 'slowapi' package is required for rate limiting. Install it via the 'api' extras."
        ) from exc


Limiter = cast(Any, _load_attr("slowapi", "Limiter"))
_rate_limit_exceeded_handler = cast(Any, _load_attr("slowapi", "_rate_limit_exceeded_handler"))
RateLimitExceeded = cast(Any, _load_attr("slowapi.errors", "RateLimitExceeded"))
get_remote_address = cast(Any, _load_attr("slowapi.util", "get_remote_address"))
SlowAPIMiddleware = cast(Any, _load_attr("slowapi.middleware", "SlowAPIMiddleware"))

limiter = Limiter(key_func=get_remote_address)

__all__ = [
    "limiter",
    "RateLimitExceeded",
    "_rate_limit_exceeded_handler",
    "SlowAPIMiddleware",
]
