from __future__ import annotations

from functools import lru_cache

from api.core.settings import Settings, get_settings
from api.services.container import (
    get_analyzer as _get_analyzer,
    get_chat_agent as _get_chat_agent,
    get_scraper as _get_scraper,
)
from api.services.orchestrator import AnalysisOrchestrator


def get_settings_dependency() -> Settings:
    return get_settings()


@lru_cache
def get_analysis_orchestrator() -> AnalysisOrchestrator:
    return AnalysisOrchestrator(
        scraper=_get_scraper(),
        analyzer=_get_analyzer(),
        chat_agent=_get_chat_agent(),
    )


def get_chat_agent():
    return _get_chat_agent()
