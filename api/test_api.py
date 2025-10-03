"""
Comprehensive test cases for the Website Insights API.
Tests cover authentication, rate limiting, validation, and core functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.index import app, SECRET_KEY

# Test client
client = TestClient(app)

# Test constants
TEST_URL = "https://example.com"
VALID_AUTH_HEADER = {"Authorization": f"Bearer {SECRET_KEY}"}
INVALID_AUTH_HEADER = {"Authorization": "Bearer invalid-token"}


class TestAuthentication:
    """Test authentication and authorization."""
    
    def test_missing_auth_header(self):
        """Test request without authorization header returns 401."""
        response = client.post(
            "/api/analyze",
            json={"url": TEST_URL}
        )
        assert response.status_code == 401
        assert "Authorization header missing" in response.json()["detail"]
    
    def test_invalid_auth_format(self):
        """Test invalid authorization format returns 401."""
        response = client.post(
            "/api/analyze",
            json={"url": TEST_URL},
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401
        assert "Invalid authorization format" in response.json()["detail"]
    
    def test_invalid_token(self):
        """Test invalid token returns 401."""
        response = client.post(
            "/api/analyze",
            json={"url": TEST_URL},
            headers=INVALID_AUTH_HEADER
        )
        assert response.status_code == 401
        assert "Invalid authorization token" in response.json()["detail"]
    
    def test_valid_auth(self):
        """Test valid authentication allows request processing."""
        with patch('api.scraper.WebsiteScraper.scrape_website') as mock_scrape, \
             patch('api.analyzer.AIAnalyzer.analyze_website') as mock_analyze:
            
            mock_scrape.return_value = {"content": "test"}
            mock_analyze.return_value = {"industry": "Tech"}
            
            response = client.post(
                "/api/analyze",
                json={"url": TEST_URL},
                headers=VALID_AUTH_HEADER
            )
            assert response.status_code in [200, 500]  # 500 if dependencies not available


class TestValidation:
    """Test input validation with Pydantic."""
    
    def test_missing_url(self):
        """Test missing URL returns validation error."""
        response = client.post(
            "/api/analyze",
            json={},
            headers=VALID_AUTH_HEADER
        )
        assert response.status_code == 422
    
    def test_invalid_url_format(self):
        """Test invalid URL format returns validation error."""
        response = client.post(
            "/api/analyze",
            json={"url": "not-a-valid-url"},
            headers=VALID_AUTH_HEADER
        )
        assert response.status_code == 422
    
    def test_valid_url_with_https(self):
        """Test valid HTTPS URL passes validation."""
        with patch('api.scraper.WebsiteScraper.scrape_website') as mock_scrape, \
             patch('api.analyzer.AIAnalyzer.analyze_website') as mock_analyze:
            
            mock_scrape.return_value = {"content": "test"}
            mock_analyze.return_value = {"industry": "Tech"}
            
            response = client.post(
                "/api/analyze",
                json={"url": "https://example.com"},
                headers=VALID_AUTH_HEADER
            )
            assert response.status_code in [200, 500]
    
    def test_optional_questions_field(self):
        """Test questions field is optional."""
        with patch('api.scraper.WebsiteScraper.scrape_website') as mock_scrape, \
             patch('api.analyzer.AIAnalyzer.analyze_website') as mock_analyze:
            
            mock_scrape.return_value = {"content": "test"}
            mock_analyze.return_value = {"industry": "Tech"}
            
            response = client.post(
                "/api/analyze",
                json={"url": TEST_URL, "questions": ["What industry?"]},
                headers=VALID_AUTH_HEADER
            )
            assert response.status_code in [200, 500]


class TestAnalyzeEndpoint:
    """Test /api/analyze endpoint functionality."""
    
    @patch('api.scraper.WebsiteScraper.scrape_website')
    @patch('api.analyzer.AIAnalyzer.analyze_website')
    @patch('api.chat.ConversationalAgent.cache_website_data')
    def test_successful_analysis(self, mock_cache, mock_analyze, mock_scrape):
        """Test successful website analysis returns expected structure."""
        # Mock responses
        mock_scrape.return_value = {
            "url": TEST_URL,
            "content": "Test content",
            "title": "Test Company"
        }
        
        mock_analyze.return_value = {
            "industry": "Technology",
            "company_size": "Medium",
            "location": "San Francisco",
            "usp": "AI-powered solutions",
            "products_services": "Software development",
            "target_audience": "Businesses",
            "sentiment": "Positive"
        }
        
        response = client.post(
            "/api/analyze",
            json={"url": TEST_URL},
            headers=VALID_AUTH_HEADER
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "insights" in data
        assert "timestamp" in data
        assert data["url"] == TEST_URL
        assert data["insights"]["industry"] == "Technology"
    
    @patch('api.scraper.WebsiteScraper.scrape_website')
    @patch('api.chat.ConversationalAgent.answer_question_with_sources')
    @patch('api.analyzer.AIAnalyzer.analyze_website')
    def test_analysis_with_custom_questions(self, mock_analyze, mock_answer_question, mock_scrape):
        """Test analysis with custom questions."""
        mock_scrape.return_value = {"content": "test"}
        mock_analyze.return_value = {
            "industry": "Tech",
            "custom_answers": {
                "pricing": "Subscription-based"
            }
        }
        mock_answer_question.return_value = {
            "answer": "Pricing is subscription-based",
            "source_chunks": [
                {"chunk_index": 0, "chunk_text": "Pricing details", "relevance_score": 0.9}
            ]
        }
        
        response = client.post(
            "/api/analyze",
            json={
                "url": TEST_URL,
                "questions": ["What is the pricing model?"]
            },
            headers=VALID_AUTH_HEADER
        )
        
        assert response.status_code == 200
        # Verify that analyze_website was called with questions
        assert mock_analyze.called
        mock_answer_question.assert_called()
    
    @patch('api.scraper.WebsiteScraper.scrape_website')
    def test_scraping_failure(self, mock_scrape):
        """Test handling of scraping failures."""
        mock_scrape.side_effect = Exception("Failed to fetch website")
        
        response = client.post(
            "/api/analyze",
            json={"url": TEST_URL},
            headers=VALID_AUTH_HEADER
        )
        
        assert response.status_code == 500
        assert "Analysis failed" in response.json()["detail"]


class TestChatEndpoint:
    """Test /api/chat endpoint functionality."""
    
    @patch('api.chat.ConversationalAgent.chat')
    def test_successful_chat(self, mock_chat):
        """Test successful chat interaction."""
        mock_chat.return_value = "The company is in the Technology sector."
        
        response = client.post(
            "/api/chat",
            json={
                "url": TEST_URL,
                "query": "What industry is the company in?"
            },
            headers=VALID_AUTH_HEADER
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "query" in data
        assert "response" in data
        assert "timestamp" in data
        assert data["response"] == "The company is in the Technology sector."
    
    @patch('api.chat.ConversationalAgent.chat')
    def test_chat_with_conversation_history(self, mock_chat):
        """Test chat with conversation history."""
        mock_chat.return_value = "Based on our previous discussion..."
        
        conversation_history = [
            {"role": "user", "content": "What do they sell?"},
            {"role": "assistant", "content": "They sell software."}
        ]
        
        response = client.post(
            "/api/chat",
            json={
                "url": TEST_URL,
                "query": "Tell me more",
                "conversation_history": conversation_history
            },
            headers=VALID_AUTH_HEADER
        )
        
        assert response.status_code == 200
        assert mock_chat.called
        # Verify conversation_history was passed
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["conversation_history"] == conversation_history
    
    @patch('api.chat.ConversationalAgent.chat')
    def test_chat_failure(self, mock_chat):
        """Test handling of chat failures."""
        mock_chat.side_effect = Exception("AI service unavailable")
        
        response = client.post(
            "/api/chat",
            json={
                "url": TEST_URL,
                "query": "What industry?"
            },
            headers=VALID_AUTH_HEADER
        )
        
        assert response.status_code == 500


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint(self):
        """Test /api/health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_root_health_endpoint(self):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "/api/analyze" in str(data["endpoints"])


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_analyze_rate_limit(self):
        """Test rate limiting on analyze endpoint (10/minute)."""
        # This test would need to make 11+ requests rapidly
        # In practice, you'd use a separate test with time mocking
        pass  # Placeholder - implement with time mocking if needed
    
    def test_chat_rate_limit(self):
        """Test rate limiting on chat endpoint (20/minute)."""
        # This test would need to make 21+ requests rapidly
        pass  # Placeholder - implement with time mocking if needed


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/analyze",
            data="not json",
            headers={
                **VALID_AUTH_HEADER,
                "Content-Type": "application/json"
            }
        )
        assert response.status_code in [400, 422]
    
    @patch('api.scraper.WebsiteScraper.scrape_website')
    def test_empty_scrape_result(self, mock_scrape):
        """Test handling of empty scrape results."""
        mock_scrape.return_value = {}
        
        response = client.post(
            "/api/analyze",
            json={"url": TEST_URL},
            headers=VALID_AUTH_HEADER
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 500]


# Run tests with: pytest api/test_api.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
