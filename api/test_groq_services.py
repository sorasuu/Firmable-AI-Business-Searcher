import os

from api.groq_services import GroqCompoundClient


def test_groq_client_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    client = GroqCompoundClient(enable_visit=True, enable_browser_automation=True)

    assert client.client is None
    assert client.visit_website("https://example.com") is None
    assert client.browser_research("What is new?", focus_url="https://example.com") is None
