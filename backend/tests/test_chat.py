"""
Tests for the chat router (POST /api/chat).

Ollama, the vector store, and the embedding service are all mocked so these
tests run without any external services.

SSE responses are read as plain text: each event is a line of the form
``data: <content>`` and the stream ends with ``data: [DONE]``.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse(text: str) -> list[str]:
    """Extract the data values from a raw SSE response body."""
    values = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            values.append(line[len("data:"):].strip())
    return values


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------


class TestChatAuth:
    """The endpoint must reject unauthenticated requests."""

    def test_no_token_returns_401(self, client: TestClient) -> None:
        response = client.post("/api/chat", json={"query": "What is the revenue?"})
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer not.a.real.token"},
            json={"query": "What is the revenue?"},
        )
        assert response.status_code == 401

    def test_missing_query_field_returns_422(
        self, client: TestClient, token_finance: str
    ) -> None:
        response = client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token_finance}"},
            json={},
        )
        assert response.status_code == 422

    def test_empty_query_returns_400(
        self, client: TestClient, token_finance: str
    ) -> None:
        response = client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token_finance}"},
            json={"query": "   "},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Successful streaming response
# ---------------------------------------------------------------------------


class TestChatStream:
    """Happy-path tests: valid token + mocked downstream services."""

    def test_finance_user_gets_sse_stream(
        self,
        client: TestClient,
        token_finance: str,
        sample_chunks: list[dict],
        make_stream_generator,
    ) -> None:
        """A finance user receives an SSE stream containing tokens and [DONE]."""
        tokens = ["The ", "Q3 ", "revenue ", "was ", "$4.2M."]

        with (
            patch(
                "app.routers.chat.query_documents",
                return_value=sample_chunks,
            ),
            patch(
                "app.routers.chat.stream_response",
                side_effect=make_stream_generator(tokens),
            ),
        ):
            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token_finance}"},
                json={"query": "What was the Q3 revenue?"},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        data_values = _parse_sse(response.text)
        assert "[DONE]" in data_values

        # All yielded tokens should appear in the stream.
        combined = "".join(v for v in data_values if v != "[DONE]")
        assert "Q3" in combined

    def test_stream_ends_with_done_sentinel(
        self,
        client: TestClient,
        token_hr: str,
        sample_chunks: list[dict],
        make_stream_generator,
    ) -> None:
        """The last SSE event must always be [DONE]."""
        with (
            patch("app.routers.chat.query_documents", return_value=sample_chunks),
            patch(
                "app.routers.chat.stream_response",
                side_effect=make_stream_generator(["Hello"]),
            ),
        ):
            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token_hr}"},
                json={"query": "Tell me about leave policy."},
            )

        data_values = _parse_sse(response.text)
        assert data_values[-1] == "[DONE]"

    def test_conversation_history_is_forwarded(
        self,
        client: TestClient,
        token_engineering: str,
        sample_chunks: list[dict],
        make_stream_generator,
    ) -> None:
        """History passed in the request body is forwarded to the LLM service."""
        captured: dict = {}

        async def _capture_stream(query, chunks, history):
            captured["history"] = history
            for token in ["ok"]:
                yield token

        with (
            patch("app.routers.chat.query_documents", return_value=sample_chunks),
            patch("app.routers.chat.stream_response", side_effect=_capture_stream),
        ):
            client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token_engineering}"},
                json={
                    "query": "What is the CI pipeline?",
                    "history": [
                        {"role": "user",      "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"},
                    ],
                },
            )

        assert len(captured.get("history", [])) == 2
        assert captured["history"][0]["role"] == "user"


# ---------------------------------------------------------------------------
# No relevant chunks found
# ---------------------------------------------------------------------------


class TestChatNoChunks:
    """When the vector store returns no chunks, a fallback message is streamed."""

    def test_no_chunks_streams_fallback_message(
        self, client: TestClient, token_finance: str
    ) -> None:
        with patch("app.routers.chat.query_documents", return_value=[]):
            response = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token_finance}"},
                json={"query": "What is the meaning of life?"},
            )

        assert response.status_code == 200
        data_values = _parse_sse(response.text)
        combined = " ".join(data_values)
        assert "relevant" in combined.lower() or "information" in combined.lower()
        assert "[DONE]" in data_values


# ---------------------------------------------------------------------------
# RBAC — cross-department access is blocked at the vector store level
# ---------------------------------------------------------------------------


class TestChatRBAC:
    """Role-scoped access is reflected in the allowed_sources forwarded to the store."""

    def test_employee_query_uses_only_handbook_source(
        self,
        client: TestClient,
        token_employee: str,
        make_stream_generator,
    ) -> None:
        """An employee token results in only employee_handbook being queried."""
        captured: dict = {}

        def _capture_query(embedding, allowed_sources, k=5):
            captured["allowed_sources"] = allowed_sources
            return []  # No chunks — triggers fallback message.

        with patch("app.routers.chat.query_documents", side_effect=_capture_query):
            client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token_employee}"},
                json={"query": "What are the holiday benefits?"},
            )

        assert captured.get("allowed_sources") == ["employee_handbook"]

    def test_c_level_query_uses_all_sources(
        self,
        client: TestClient,
        token_c_level: str,
    ) -> None:
        """A c_level token results in all five departments being queried."""
        captured: dict = {}

        def _capture_query(embedding, allowed_sources, k=5):
            captured["allowed_sources"] = allowed_sources
            return []

        with patch("app.routers.chat.query_documents", side_effect=_capture_query):
            client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token_c_level}"},
                json={"query": "Give me a full company overview."},
            )

        expected = {"employee_handbook", "hr", "finance", "marketing", "engineering"}
        assert set(captured.get("allowed_sources", [])) == expected
