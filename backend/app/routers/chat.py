"""
Chat router — streaming RAG responses over Server-Sent Events.

Full request flow
-----------------
1. Verify JWT → extract role + email.
2. Resolve allowed document collections for that role (RBAC).
3. **Keyword check** — if the query touches a restricted department,
   return an access-denied message immediately (no LLM / ChromaDB call).
4. Embed the user query via the local sentence-transformer model.
5. Query ChromaDB with an RBAC ``where`` filter to retrieve relevant chunks.
6. Stream the Ollama LLM response token-by-token back to the client as SSE.

Endpoint
--------
POST /api/chat
"""

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.services.embed_service import embed_text
from app.services.llm_service import stream_response
from app.services.rbac_service import detect_restricted_topic, get_allowed_sources
from app.services.vector_service import query_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class MessageHistory(BaseModel):
    """A single turn in the conversation history."""
    role:    str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Payload expected by POST /api/chat."""
    query:   str
    history: list[MessageHistory] = []


# ---------------------------------------------------------------------------
# SSE stream helpers
# ---------------------------------------------------------------------------


async def _token_stream(
    query: str,
    chunks: list[dict],
    history: list[dict],
    role: str,
    allowed_sources: list[str],
) -> AsyncGenerator[dict, None]:
    """Wrap ``llm_service.stream_response`` in SSE event dicts."""
    try:
        async for token in stream_response(query, chunks, history, role, allowed_sources):
            yield {"data": json.dumps(token)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while streaming LLM response: %s", exc)
        yield {"data": json.dumps("[ERROR] An unexpected error occurred.")}
    finally:
        yield {"data": "[DONE]"}


async def _denied_stream(message: str) -> AsyncGenerator[dict, None]:
    """Yield a JSON-encoded access-denied message then [DONE]."""
    yield {"data": json.dumps(message)}
    yield {"data": "[DONE]"}


async def _error_stream(message: str) -> AsyncGenerator[dict, None]:
    """Yield a plain error string then [DONE]."""
    yield {"data": message}
    yield {"data": "[DONE]"}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> EventSourceResponse:
    """Stream a RAG-generated answer to the user's query via Server-Sent Events.

    Restricted topic queries are intercepted before the vector store is
    consulted and an access-denied message is returned directly.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty.",
        )

    role:  str = current_user["role"]
    email: str = current_user["email"]
    print(f"[CHAT] User: {email} | Role: {role}")

    # Step 1: Resolve RBAC — raises ValueError for unknown roles.
    try:
        allowed_sources = get_allowed_sources(role)
    except ValueError as exc:
        logger.warning("RBAC rejection for role '%s': %s", role, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    print(f"[CHAT] Allowed sources: {allowed_sources}")

    # Step 2: Keyword-based restricted-topic check (fast path — no DB/LLM call).
    restriction = detect_restricted_topic(query, role)
    if restriction["is_restricted"]:
        print(
            f"[CHAT] BLOCKED: {email} (role={role}) asked about "
            f"'{restriction['restricted_topic']}'"
        )
        return EventSourceResponse(
            _denied_stream(restriction["access_denied_message"])
        )

    # Step 3: Embed the query.
    try:
        query_embedding = embed_text(query)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Embedding failed for query %r: %s", query, exc)
        return EventSourceResponse(
            _error_stream("[ERROR] Failed to process your query. Please try again.")
        )

    # Step 4: Query ChromaDB with the RBAC filter.
    try:
        chunks = query_documents(query_embedding, allowed_sources, k=5)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Vector store query failed: %s", exc)
        return EventSourceResponse(
            _error_stream("[ERROR] Failed to retrieve relevant documents. Please try again.")
        )
    print(f"[CHAT] Chunks found: {len(chunks)}")
    if chunks:
        print(f"[CHAT] First chunk source: {chunks[0]['metadata'].get('source')}")
    else:
        print("[CHAT] NO CHUNKS FOUND — context will be empty")

    # Step 5: Double RBAC check — filter out any chunk from a dept the role cannot access.
    safe_chunks = []
    for chunk in chunks:
        chunk_dept = chunk.get("metadata", {}).get("department", "")
        if chunk_dept in allowed_sources:
            safe_chunks.append(chunk)
        else:
            print(
                f"[SECURITY] Filtered chunk: dept={chunk_dept}, role={role}"
            )
    chunks = safe_chunks
    print(f"[CHAT] Safe chunks: {len(chunks)}")

    # Step 7: No safe chunks — check whether a restriction was bypassed before
    # falling back to the LLM with empty context (which would cause hallucination).
    if not chunks:
        logger.info("No safe chunks found for role='%s', query=%r", role, query[:80])

        # Re-run the restriction check: the initial pass (Step 2) uses regex
        # patterns — if a query slipped through there and ChromaDB returned only
        # chunks from departments the role cannot access, we surface the proper
        # access-denied message instead of a generic "no info" reply.
        post_restriction = detect_restricted_topic(query, role)
        if post_restriction["is_restricted"]:
            print(
                f"[CHAT] POST-FILTER BLOCK: {email} (role={role}) — "
                f"topic={post_restriction['restricted_topic']}"
            )
            return EventSourceResponse(
                _denied_stream(post_restriction["access_denied_message"])
            )

        # Genuinely no data available for this role and query.
        return EventSourceResponse(
            _error_stream(
                "I don't have relevant information in your authorized documents "
                "to answer this question."
            )
        )

    # Step 8: Stream LLM tokens back to the client.
    history = [m.dict() for m in request.history]

    logger.info(
        "Streaming response | user=%s role=%s chunks=%d query=%r",
        email, role, len(chunks), query[:80],
    )

    return EventSourceResponse(
        _token_stream(query, chunks, history, role, allowed_sources)
    )
