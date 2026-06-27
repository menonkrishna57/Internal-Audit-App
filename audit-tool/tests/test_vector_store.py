"""
test_vector_store.py — Tests for the Qdrant/Jina vector store module.

These tests use mocking so they run without a live Qdrant instance or
Jina API key. Integration tests that hit the real services are marked
with @pytest.mark.integration and skipped by default.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.policy_engine.models import PolicyClause


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_clause() -> PolicyClause:
    return PolicyClause(
        clause_id="4.3.1",
        title="Account Inactivity Policy",
        full_text="Accounts inactive for more than 30 days shall be suspended.",
        page_number=5,
        section_path="4. Access Control > 4.3 Account Management",
        source_pdf="it_security_policy.pdf",
        policy_version="2.1",
        upload_timestamp=datetime(2026, 6, 23, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def sample_clauses(sample_clause) -> list[PolicyClause]:
    return [
        sample_clause,
        PolicyClause(
            clause_id="5.1.1",
            title="Password Rotation",
            full_text="Service account passwords must be rotated every 90 days.",
            page_number=8,
            section_path="5. Authentication > 5.1 Passwords",
            source_pdf="it_security_policy.pdf",
            policy_version="2.1",
        ),
    ]


@pytest.fixture()
def fake_vector() -> list[float]:
    """Returns a fake 1024-dimensional unit vector."""
    v = [0.0] * 1024
    v[0] = 1.0
    return v


# ---------------------------------------------------------------------------
# embed_texts
# ---------------------------------------------------------------------------

class TestEmbedTexts:
    def test_raises_without_api_key(self):
        from app.policy_engine import vector_store
        with patch.object(vector_store.settings, "jina_api_key", ""):
            from app.policy_engine.vector_store import embed_texts
            with pytest.raises(RuntimeError, match="JINA_API_KEY"):
                embed_texts(["hello world"])

    def test_returns_correct_number_of_vectors(self, fake_vector):
        with patch("app.policy_engine.vector_store.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "data": [
                    {"embedding": fake_vector},
                    {"embedding": fake_vector},
                ]
            }
            mock_post.return_value = mock_response

            from app.policy_engine.vector_store import embed_texts
            with patch("app.policy_engine.vector_store.settings") as mock_settings:
                mock_settings.jina_api_key = "jina_test_key"
                mock_settings.jina_embedding_model = "jina-embeddings-v3"
                mock_settings.jina_embedding_dimensions = 1024
                result = embed_texts(["text one", "text two"])

            assert len(result) == 2
            assert len(result[0]) == 1024


# ---------------------------------------------------------------------------
# upsert_clauses
# ---------------------------------------------------------------------------

class TestUpsertClauses:
    def test_empty_list_returns_zero(self):
        from app.policy_engine.vector_store import upsert_clauses
        result = upsert_clauses([])
        assert result == 0

    def test_upsert_calls_qdrant_with_correct_count(self, sample_clauses, fake_vector):
        with (
            patch("app.policy_engine.vector_store.embed_texts") as mock_embed,
            patch("app.policy_engine.vector_store.ensure_collection"),
            patch("app.policy_engine.vector_store.get_qdrant_client") as mock_client_fn,
        ):
            mock_embed.return_value = [fake_vector, fake_vector]
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client

            from app.policy_engine.vector_store import upsert_clauses
            with patch("app.policy_engine.vector_store.settings") as mock_settings:
                mock_settings.qdrant_collection = "test_collection"
                count = upsert_clauses(sample_clauses)

            assert count == 2
            mock_client.upsert.assert_called_once()

    def test_deterministic_ids_are_consistent(self, sample_clause, fake_vector):
        """Re-upserting the same clause should produce the same Qdrant point ID."""
        captured_ids = []

        def capture_upsert(collection_name, points):
            captured_ids.extend([p.id for p in points])

        with (
            patch("app.policy_engine.vector_store.embed_texts", return_value=[fake_vector]),
            patch("app.policy_engine.vector_store.ensure_collection"),
            patch("app.policy_engine.vector_store.get_qdrant_client") as mock_client_fn,
        ):
            mock_client = MagicMock()
            mock_client.upsert.side_effect = capture_upsert
            mock_client_fn.return_value = mock_client

            from app.policy_engine.vector_store import upsert_clauses
            with patch("app.policy_engine.vector_store.settings") as mock_settings:
                mock_settings.qdrant_collection = "test_collection"
                upsert_clauses([sample_clause])
                upsert_clauses([sample_clause])

        assert len(captured_ids) == 2
        assert captured_ids[0] == captured_ids[1], "Same clause should produce same Qdrant ID"


# ---------------------------------------------------------------------------
# search_clauses
# ---------------------------------------------------------------------------

class TestSearchClauses:
    def test_returns_expected_shape(self, fake_vector):
        mock_hit = MagicMock()
        mock_hit.score = 0.91
        mock_hit.payload = {"title": "Account Inactivity", "clause_id": "4.3.1"}
        mock_hit.id = "abc-123"

        mock_result = MagicMock()
        mock_result.points = [mock_hit]

        with (
            patch("app.policy_engine.vector_store.embed_texts", return_value=[fake_vector]),
            patch("app.policy_engine.vector_store.ensure_collection"),
            patch("app.policy_engine.vector_store.get_qdrant_client") as mock_client_fn,
        ):
            mock_client = MagicMock()
            mock_client.query_points.return_value = mock_result
            mock_client_fn.return_value = mock_client

            from app.policy_engine.vector_store import search_clauses
            with patch("app.policy_engine.vector_store.settings") as mock_settings:
                mock_settings.qdrant_collection = "test_collection"
                results = search_clauses("inactive accounts", top_k=1)

        assert len(results) == 1
        assert results[0]["score"] == pytest.approx(0.91)
        assert "payload" in results[0]
        assert "id" in results[0]
