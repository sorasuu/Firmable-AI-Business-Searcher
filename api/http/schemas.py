from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, HttpUrl


class AnalysisRequest(BaseModel):
    url: HttpUrl
    questions: Optional[List[str]] = None
    session_id: Optional[str] = None


class ConversationRequest(BaseModel):
    url: HttpUrl
    query: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None


class AnalysisResponse(BaseModel):
    url: str
    insights: Dict[str, Any]
    timestamp: str
    session_id: str


class ConversationResponse(BaseModel):
    url: str
    query: str
    response: str
    timestamp: str
    session_id: str
