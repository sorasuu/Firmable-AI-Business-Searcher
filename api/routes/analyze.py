from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from api.core.rate_limiter import limiter
from api.core.security import verify_auth
from api.http.schemas import AnalysisRequest, AnalysisResponse
from api.services.orchestrator import AnalysisOrchestrator
from api.dependencies import get_analysis_orchestrator

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("10/minute")
async def analyze_website(
    request: Request,
    payload: AnalysisRequest = Body(...),
    _: None = Depends(verify_auth),
    orchestrator: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> AnalysisResponse:
    try:
        insights = orchestrator.analyze(str(payload.url), payload.questions)
    except Exception as exc:  # pragma: no cover - FastAPI handles HTTPException generation
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    return AnalysisResponse(
        url=str(payload.url),
        insights=insights,
    timestamp=datetime.now(timezone.utc).isoformat(),
    )
