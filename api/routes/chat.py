import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from api.chat import ConversationalAgent
from api.core.rate_limiter import limiter
from api.core.security import verify_auth
from api.core.settings import get_settings
from api.dependencies import get_chat_agent
from api.http.schemas import ConversationRequest, ConversationResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ConversationResponse)
@limiter.limit(lambda: get_settings().rate_limit_chat)
async def chat_about_website(
    request: Request,
    payload: ConversationRequest = Body(...),
    _: None = Depends(verify_auth),
    chat_agent: ConversationalAgent = Depends(get_chat_agent),
) -> ConversationResponse:
    # Use provided session_id to ensure context isolation
    session_id = payload.session_id
    
    try:
        # Offload blocking operations to thread pool to prevent event loop blocking
        response_text = await asyncio.to_thread(
            chat_agent.chat,
            url=str(payload.url),
            query=payload.query,
            conversation_history=payload.conversation_history,
            session_id=session_id,
        )
    except Exception as exc:  # pragma: no cover - FastAPI handles HTTPException generation
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ConversationResponse(
        url=str(payload.url),
        query=payload.query,
        response=response_text,
        timestamp=datetime.now(timezone.utc).isoformat(),
        session_id=session_id or "default",
    )
