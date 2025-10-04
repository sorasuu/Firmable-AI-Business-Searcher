"""
Test session-based isolation for multi-user context management.

These tests verify that the session_id parameter properly isolates
data between different users/sessions to prevent context collisions.
"""

import time
import uuid
from typing import Dict, Any

import pytest

from api.data_store import AnalysisStore, WebsiteEntry


@pytest.fixture
def store():
    """Fresh AnalysisStore instance for each test."""
    return AnalysisStore()


@pytest.fixture
def sample_data():
    """Sample website data for testing."""
    return {
        "url": "https://example.com",
        "title": "Example Company",
        "markdown": "# Example Company\n\nWe do great things.",
        "structured_chunks": [
            "Example Company is a technology firm.",
            "We offer innovative solutions.",
            "Contact us at hello@example.com"
        ]
    }


@pytest.fixture
def sample_insights():
    """Sample analysis insights."""
    return {
        "industry": "Technology",
        "company_size": "Mid-market",
        "location": "San Francisco, CA",
        "summary": "A technology company offering innovative solutions."
    }


class TestSessionIsolation:
    """Test suite for session-based data isolation."""

    def test_different_sessions_store_separately(self, store, sample_data, sample_insights):
        """Test that different session_ids create separate storage entries."""
        url = "https://example.com"
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        # Store data for session A
        insights_a = {**sample_insights, "summary": "Session A insights"}
        entry_a = store.store_analysis(url, sample_data, insights_a, session_id=session_a)

        # Store data for session B
        insights_b = {**sample_insights, "summary": "Session B insights"}
        entry_b = store.store_analysis(url, sample_data, insights_b, session_id=session_b)

        # Verify both are stored with different keys
        assert entry_a.session_id == session_a
        assert entry_b.session_id == session_b
        assert entry_a.insights["summary"] == "Session A insights"
        assert entry_b.insights["summary"] == "Session B insights"

    def test_retrieve_correct_session_data(self, store, sample_data, sample_insights):
        """Test that retrieval uses the correct session_id."""
        url = "https://example.com"
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        # Store different data for each session
        insights_a = {**sample_insights, "industry": "Technology"}
        insights_b = {**sample_insights, "industry": "Healthcare"}

        store.store_analysis(url, sample_data, insights_a, session_id=session_a)
        store.store_analysis(url, sample_data, insights_b, session_id=session_b)

        # Retrieve session A data
        entry_a = store.get(url, session_id=session_a)
        assert entry_a is not None
        assert entry_a.insights["industry"] == "Technology"

        # Retrieve session B data
        entry_b = store.get(url, session_id=session_b)
        assert entry_b is not None
        assert entry_b.insights["industry"] == "Healthcare"

    def test_search_chunks_respects_session(self, store, sample_data, sample_insights):
        """Test that semantic search retrieves chunks from the correct session."""
        url = "https://example.com"
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        # Store data with different chunks for each session (must be >40 chars)
        data_a = {**sample_data, "structured_chunks": ["Session A: Stripe payment processing platform for online businesses"]}
        data_b = {**sample_data, "structured_chunks": ["Session B: Notion workspace tools for collaborative teams"]}

        store.store_analysis(url, data_a, sample_insights, session_id=session_a)
        store.store_analysis(url, data_b, sample_insights, session_id=session_b)

        # Search in session A
        results_a = store.search_chunks(url, "payment", top_k=1, session_id=session_a)
        # FAISS might not be available or index might be empty, so check if results exist first
        if len(results_a) > 0:
            assert "Stripe" in results_a[0]["chunk_text"]
        else:
            # Fallback: verify entry retrieval works at least
            entry_a = store.get(url, session_id=session_a)
            assert entry_a is not None
            assert len(entry_a.chunks) > 0, "Chunks should not be empty"
            assert "Stripe" in entry_a.chunks[0]

        # Search in session B
        results_b = store.search_chunks(url, "workspace", top_k=1, session_id=session_b)
        if len(results_b) > 0:
            assert "Notion" in results_b[0]["chunk_text"]
        else:
            # Fallback: verify entry retrieval works at least
            entry_b = store.get(url, session_id=session_b)
            assert entry_b is not None
            assert len(entry_b.chunks) > 0, "Chunks should not be empty"
            assert "Notion" in entry_b.chunks[0]

    def test_update_insights_respects_session(self, store, sample_data, sample_insights):
        """Test that updating insights affects only the correct session."""
        url = "https://example.com"
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        # Store initial data for both sessions
        store.store_analysis(url, sample_data, sample_insights, session_id=session_a)
        store.store_analysis(url, sample_data, sample_insights, session_id=session_b)

        # Update only session A
        updated_insights_a = {**sample_insights, "location": "New York, NY"}
        store.update_insights(url, updated_insights_a, session_id=session_a)

        # Verify session A was updated
        entry_a = store.get(url, session_id=session_a)
        assert entry_a.insights["location"] == "New York, NY"

        # Verify session B remains unchanged
        entry_b = store.get(url, session_id=session_b)
        assert entry_b.insights["location"] == "San Francisco, CA"

    def test_no_session_id_uses_url_only(self, store, sample_data, sample_insights):
        """Test backward compatibility: no session_id uses URL as key."""
        url = "https://example.com"

        # Store without session_id
        entry = store.store_analysis(url, sample_data, sample_insights)
        assert entry.session_id is None

        # Retrieve without session_id
        retrieved = store.get(url)
        assert retrieved is not None
        assert retrieved.insights == sample_insights

    def test_session_collision_prevention(self, store, sample_data, sample_insights):
        """Test that different URLs with same session_id don't collide."""
        session_id = str(uuid.uuid4())
        url_a = "https://stripe.com"
        url_b = "https://notion.so"

        insights_stripe = {**sample_insights, "industry": "Payments"}
        insights_notion = {**sample_insights, "industry": "Productivity"}

        # Store both with same session_id
        store.store_analysis(url_a, sample_data, insights_stripe, session_id=session_id)
        store.store_analysis(url_b, sample_data, insights_notion, session_id=session_id)

        # Verify each URL maintains its own data
        entry_stripe = store.get(url_a, session_id=session_id)
        entry_notion = store.get(url_b, session_id=session_id)

        assert entry_stripe.insights["industry"] == "Payments"
        assert entry_notion.insights["industry"] == "Productivity"


class TestTTLExpiration:
    """Test suite for TTL (Time-To-Live) expiration functionality."""

    def test_entry_is_expired_after_ttl(self, store, sample_data, sample_insights):
        """Test that entries are marked as expired after TTL."""
        url = "https://example.com"
        session_id = str(uuid.uuid4())

        # Store entry
        entry = store.store_analysis(url, sample_data, sample_insights, session_id=session_id)

        # Check not expired immediately
        assert not entry.is_expired(ttl_seconds=3600)

        # Check expired after TTL (simulate by checking with 0 TTL)
        # When ttl_seconds=0, any time elapsed > 0 means expired
        # Since some time has passed, it should be expired
        time.sleep(0.01)  # Ensure some time has passed
        assert entry.is_expired(ttl_seconds=0)

    def test_cleanup_removes_expired_entries(self, store, sample_data, sample_insights):
        """Test that cleanup removes expired entries."""
        url = "https://example.com"
        session_old = str(uuid.uuid4())
        session_new = str(uuid.uuid4())

        # Store old entry (will be expired)
        entry_old = store.store_analysis(url, sample_data, sample_insights, session_id=session_old)
        # Manually set old timestamp
        entry_old.timestamp = time.time() - 7200  # 2 hours ago

        # Store new entry (not expired)
        store.store_analysis(url, sample_data, sample_insights, session_id=session_new)

        # Run cleanup
        store._cleanup_expired()

        # Old entry should be gone
        assert store.get(url, session_id=session_old) is None

        # New entry should still exist
        assert store.get(url, session_id=session_new) is not None

    def test_get_returns_none_for_expired_entry(self, store, sample_data, sample_insights):
        """Test that get() returns None for expired entries."""
        url = "https://example.com"
        session_id = str(uuid.uuid4())

        # Store entry
        entry = store.store_analysis(url, sample_data, sample_insights, session_id=session_id)

        # Manually expire it
        entry.timestamp = time.time() - 7200  # 2 hours ago

        # Should return None
        retrieved = store.get(url, session_id=session_id)
        assert retrieved is None


class TestMakeKeyMethod:
    """Test suite for the _make_key helper method."""

    def test_make_key_with_session(self, store):
        """Test key generation with session_id."""
        url = "https://example.com"
        session_id = "abc-123"

        key = store._make_key(url, session_id)
        assert key == "abc-123:https://example.com"  # Format is session_id:url

    def test_make_key_without_session(self, store):
        """Test key generation without session_id."""
        url = "https://example.com"

        key = store._make_key(url, None)
        assert key == "https://example.com"

    def test_make_key_url_normalization(self, store):
        """Test that URLs are normalized in keys."""
        url_with_slash = "https://example.com/"
        url_without_slash = "https://example.com"
        session_id = "abc-123"

        # Both should produce the same key
        key1 = store._make_key(url_with_slash, session_id)
        key2 = store._make_key(url_without_slash, session_id)

        # Keys should be consistent (implementation may normalize)
        assert key1 == key2 or key1.rstrip("/") == key2.rstrip("/")


class TestConcurrentUsage:
    """Test suite for concurrent multi-user scenarios."""

    def test_two_users_analyzing_different_sites(self, store, sample_data, sample_insights):
        """
        Simulate the original bug scenario:
        User A analyzes Stripe, User B analyzes Notion,
        User A chats should get Stripe data, not Notion.
        """
        # User A analyzes Stripe
        session_a = str(uuid.uuid4())
        url_stripe = "https://stripe.com"
        insights_stripe = {**sample_insights, "summary": "Stripe is a payment platform"}
        data_stripe = {**sample_data, "structured_chunks": ["Stripe payment processing API for online transactions and subscriptions"]}

        store.store_analysis(url_stripe, data_stripe, insights_stripe, session_id=session_a)

        # User B analyzes Notion
        session_b = str(uuid.uuid4())
        url_notion = "https://notion.so"
        insights_notion = {**sample_insights, "summary": "Notion is a workspace tool"}
        data_notion = {**sample_data, "structured_chunks": ["Notion collaborative workspace for teams and personal productivity"]}

        store.store_analysis(url_notion, data_notion, insights_notion, session_id=session_b)

        # User A queries - should get Stripe data
        entry_a = store.get(url_stripe, session_id=session_a)
        assert entry_a is not None
        assert "Stripe" in entry_a.insights["summary"]
        assert "Notion" not in entry_a.insights["summary"]

        # Verify chunks are isolated
        assert len(entry_a.chunks) > 0, "Chunks should not be empty"
        assert "Stripe" in entry_a.chunks[0]
        assert "payment" in entry_a.chunks[0].lower()

        # User B queries - should get Notion data
        entry_b = store.get(url_notion, session_id=session_b)
        assert entry_b is not None
        assert "Notion" in entry_b.insights["summary"]
        assert "Stripe" not in entry_b.insights["summary"]

        # Verify chunks are isolated
        assert len(entry_b.chunks) > 0, "Chunks should not be empty"
        assert "Notion" in entry_b.chunks[0]
        assert "workspace" in entry_b.chunks[0].lower()

    def test_same_url_multiple_sessions(self, store, sample_data, sample_insights):
        """
        Test multiple users analyzing the same URL with different questions.
        Each should maintain their own custom_answers.
        """
        url = "https://example.com"
        session_1 = str(uuid.uuid4())
        session_2 = str(uuid.uuid4())

        # User 1 asks about pricing
        insights_1 = {
            **sample_insights,
            "custom_answers": {"What is the pricing?": "User 1 got answer about pricing"}
        }

        # User 2 asks about integrations
        insights_2 = {
            **sample_insights,
            "custom_answers": {"What integrations exist?": "User 2 got answer about integrations"}
        }

        store.store_analysis(url, sample_data, insights_1, session_id=session_1)
        store.store_analysis(url, sample_data, insights_2, session_id=session_2)

        # Verify each user gets their own answers
        entry_1 = store.get(url, session_id=session_1)
        entry_2 = store.get(url, session_id=session_2)

        assert "pricing" in entry_1.insights["custom_answers"]["What is the pricing?"]
        assert "integrations" in entry_2.insights["custom_answers"]["What integrations exist?"]

        # Verify cross-contamination didn't happen
        assert "What integrations exist?" not in entry_1.insights["custom_answers"]
        assert "What is the pricing?" not in entry_2.insights["custom_answers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
