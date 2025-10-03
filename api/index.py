from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.core.rate_limiter import (
    RateLimitExceeded,
    SlowAPIMiddleware,
    _rate_limit_exceeded_handler,
    limiter,
)
from api.core.settings import get_settings
from api.routes import analyze, chat, system

settings = get_settings()
SECRET_KEY = settings.secret_key

app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(analyze.router)
app.include_router(chat.router)


def _format_validation_payload(exc: Any) -> dict[str, Any]:
    payload = {
        "detail": "Validation error",
        "errors": getattr(exc, "errors", lambda: [])(),
        "body": getattr(exc, "body", None),
    }
    print(f"[API] Validation error: {payload}")
    return payload


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:  # pragma: no cover - runtime hook
    return JSONResponse(status_code=422, content=_format_validation_payload(exc))


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # pragma: no cover - runtime hook
    return JSONResponse(status_code=422, content=_format_validation_payload(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - runtime hook
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
        },
    )


if __name__ == "__main__":  # pragma: no cover - convenience execution path
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
