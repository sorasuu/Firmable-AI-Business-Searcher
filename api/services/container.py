from __future__ import annotations

from functools import lru_cache

from api.analyzer import AIAnalyzer
from api.services.conversational_agent import ConversationalAgent
from api.groq_services import GroqCompoundClient
from api.scraper import WebsiteScraper


@lru_cache
def get_groq_client() -> GroqCompoundClient:
    return GroqCompoundClient()


@lru_cache
def get_scraper() -> WebsiteScraper:
    return WebsiteScraper()


@lru_cache
def get_analyzer() -> AIAnalyzer:
    return AIAnalyzer(groq_client=get_groq_client())


@lru_cache
def get_chat_agent() -> ConversationalAgent:
    return ConversationalAgent(groq_client=get_groq_client())
