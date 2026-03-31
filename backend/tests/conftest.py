"""
Shared pytest fixtures for the FinSolve backend test suite.

``embed_service`` does not exist until that module is created, so we stub it
out via ``sys.modules`` **before** the FastAPI app is imported.  This prevents
an ``ImportError`` and lets every test control embedding behaviour explicitly.
"""

import sys
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Stub embed_service before the app (and its routers) are imported.
# Any test that needs different embedding behaviour can patch the module
# attributes directly within that test.
# ---------------------------------------------------------------------------
_mock_embed = MagicMock()
_mock_embed.embed_text.return_value = [0.1] * 384
_mock_embed.embed_texts.return_value = [[0.1] * 384]
sys.modules["app.services.embed_service"] = _mock_embed

# Now it is safe to import the application.
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Synchronous ASGI test client, shared across the whole test session."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Per-role JWT token fixtures
# ---------------------------------------------------------------------------


def _token(email: str, role: str) -> str:
    return create_access_token({"sub": email, "role": role})


@pytest.fixture
def token_employee() -> str:
    return _token("eve@finsolve.com", "employee")


@pytest.fixture
def token_hr() -> str:
    return _token("carol@finsolve.com", "hr")


@pytest.fixture
def token_finance() -> str:
    return _token("alice@finsolve.com", "finance")


@pytest.fixture
def token_engineering() -> str:
    return _token("bob@finsolve.com", "engineering")


@pytest.fixture
def token_marketing() -> str:
    return _token("david@finsolve.com", "marketing")


@pytest.fixture
def token_c_level() -> str:
    return _token("frank@finsolve.com", "c_level")


# ---------------------------------------------------------------------------
# Reusable mock chunk returned by vector_service.query_documents
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_chunks() -> list[dict]:
    """One realistic-looking context chunk for chat pipeline tests."""
    return [
        {
            "text": "FinSolve Q3 revenue was $4.2 million.",
            "metadata": {"department": "finance", "source": "quarterly_financial_report.md"},
            "distance": 0.21,
        }
    ]


# ---------------------------------------------------------------------------
# Async generator factory for mocking llm_service.stream_response
# ---------------------------------------------------------------------------


def make_stream_generator(tokens: list[str]):
    """Return an async generator that yields *tokens* one by one."""

    async def _gen(*args, **kwargs) -> AsyncGenerator[str, None]:
        for token in tokens:
            yield token

    return _gen
