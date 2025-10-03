from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_analysis_orchestrator, get_chat_agent
from api.index import SECRET_KEY, app


TEST_URL = "https://example.com"


class StubChatAgent:
    def __init__(self) -> None:
        self.chat_calls = []
        self.response = "Stub chat response"
        self.raise_exc = False

    def cache_website_data(self, url, scraped_data, insights):
        pass

    def chat(self, url: str, query: str, conversation_history=None) -> str:
        self.chat_calls.append({"url": url, "query": query, "history": conversation_history})
        if self.raise_exc:
            raise RuntimeError("chat unavailable")
        return self.response


class StubOrchestrator:
    def __init__(self, chat_agent: StubChatAgent) -> None:
        self.chat_agent = chat_agent
        self.calls = []
        self.raise_exc = False

    def analyze(self, url: str, questions=None):
        self.calls.append({"url": url, "questions": list(questions) if questions else None})
        if self.raise_exc:
            raise RuntimeError("analysis failure")

        insights = {
            "industry": "Technology",
            "company_size": "Mid-market",
            "contact_info": {
                "emails": ["info@example.com"],
                "phones": ["+1 555 0100"],
                "addresses": ["123 Example Street"],
                "social_media": {"linkedin": ["https://linkedin.com/company/example"]},
            },
        }

        if questions:
            insights["custom_answers"] = {question: f"Stub answer: {question}" for question in questions}

        return insights


@pytest.fixture
def stub_services():
    chat_agent = StubChatAgent()
    orchestrator = StubOrchestrator(chat_agent)
    app.dependency_overrides[get_analysis_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_chat_agent] = lambda: chat_agent
    yield {"orchestrator": orchestrator, "chat_agent": chat_agent}
    app.dependency_overrides.clear()


@pytest.fixture
def client(stub_services):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_header():
    return {"Authorization": f"Bearer {SECRET_KEY}"}


def test_analyze_requires_authentication(client):
    response = client.post("/api/analyze", json={"url": TEST_URL})
    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header missing"


def test_analyze_rejects_invalid_token(client):
    response = client.post(
        "/api/analyze",
        json={"url": TEST_URL},
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization token"


def test_analyze_returns_insights(client, auth_header, stub_services):
    response = client.post("/api/analyze", json={"url": TEST_URL}, headers=auth_header)
    assert response.status_code == 200

    payload = response.json()
    assert payload["url"].rstrip("/") == TEST_URL.rstrip("/")
    assert payload["insights"]["industry"] == "Technology"
    assert payload["insights"]["contact_info"]["emails"] == ["info@example.com"]
    datetime.fromisoformat(payload["timestamp"])
    assert stub_services["orchestrator"].calls[-1]["questions"] is None


def test_analyze_with_questions_enriches_response(client, auth_header, stub_services):
    questions = ["What is the pricing model?"]
    response = client.post(
        "/api/analyze",
        json={"url": TEST_URL, "questions": questions},
        headers=auth_header,
    )

    assert response.status_code == 200
    insights = response.json()["insights"]
    assert insights["custom_answers"][questions[0]] == f"Stub answer: {questions[0]}"
    assert stub_services["orchestrator"].calls[-1]["questions"] == questions


def test_analyze_invalid_url_returns_422(client, auth_header):
    response = client.post(
        "/api/analyze",
        json={"url": "invalid-url"},
        headers=auth_header,
    )
    assert response.status_code == 422


def test_analyze_internal_error_returns_500(client, auth_header, stub_services):
    stub_services["orchestrator"].raise_exc = True
    response = client.post("/api/analyze", json={"url": TEST_URL}, headers=auth_header)
    assert response.status_code == 500
    assert "Analysis failed" in response.json()["detail"]


def test_chat_requires_authentication(client):
    response = client.post("/api/chat", json={"url": TEST_URL, "query": "hi"})
    assert response.status_code == 401


def test_chat_returns_agent_response(client, auth_header, stub_services):
    stub_services["chat_agent"].response = "Company operates in technology"
    response = client.post(
        "/api/chat",
        json={"url": TEST_URL, "query": "What industry?"},
        headers=auth_header,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "Company operates in technology"
    assert stub_services["chat_agent"].chat_calls[-1]["url"].rstrip("/") == TEST_URL.rstrip("/")


def test_chat_passes_conversation_history(client, auth_header, stub_services):
    history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    client.post(
        "/api/chat",
        json={"url": TEST_URL, "query": "follow up", "conversation_history": history},
        headers=auth_header,
    )
    call = stub_services["chat_agent"].chat_calls[-1]
    assert call["history"] == history


def test_chat_validation_error(client, auth_header):
    response = client.post(
        "/api/chat",
        json={"url": TEST_URL},
        headers=auth_header,
    )
    assert response.status_code == 422


def test_chat_internal_error_returns_500(client, auth_header, stub_services):
    stub_services["chat_agent"].raise_exc = True
    response = client.post(
        "/api/chat",
        json={"url": TEST_URL, "query": "hello"},
        headers=auth_header,
    )
    assert response.status_code == 500


def test_health_endpoints(client):
    assert client.get("/api/health").json() == {"status": "healthy"}
    assert client.get("/health").json() == {"status": "healthy"}
    root = client.get("/").json()
    assert root["endpoints"]["analyze"] == "/api/analyze"
    assert root["endpoints"]["chat"] == "/api/chat"


def test_rate_limit_exceeded_returns_429(client, auth_header, stub_services):
    app.state.limiter.reset()
    headers = {**auth_header, "X-Forwarded-For": "198.51.100.77"}

    response = None
    for attempt in range(11):
        response = client.post("/api/analyze", json={"url": TEST_URL}, headers=headers)
        if attempt < 10:
            assert response.status_code == 200

    assert response is not None
    assert response.status_code == 429
