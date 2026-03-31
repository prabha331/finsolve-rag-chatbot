"""
FinSolve RAG Chatbot API — application entry point.

Creates and configures the FastAPI application:
- CORS middleware scoped to the configured frontend origin.
- Auth, Chat, and Admin routers registered under their prefixes.
- Startup event: creates DB tables and seeds demo + HR users.

Run with::

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is on the path so scripts/ can be imported.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings
from app.db.database import create_all_tables
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FinSolve RAG Chatbot API",
    version="2.0.0",
    description=(
        "Internal RAG chatbot for FinSolve Technologies with role-based access control. "
        "Powered by a local Ollama LLM and ChromaDB vector store."
    ),
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)

# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    """Create DB tables and seed demo + HR users on server start."""
    print("🚀 FinSolve RAG Chatbot API starting...")
    print(f"📚 Using Ollama model: {settings.OLLAMA_MODEL}")
    print(f"🔗 Ollama URL: {settings.OLLAMA_BASE_URL}")

    # Create database tables (idempotent).
    create_all_tables()
    print("✅ Database tables ready.")

    # Seed demo users and sync HR data.
    # Wrapped in try/except so a seed failure never prevents the API from starting.
    try:
        from scripts.seed_db import seed
        seed()
    except Exception as e:
        print(f"⚠️  Seed warning: {e}")
        print("   Run `python scripts/seed_db.py` manually to seed the database.")


# ---------------------------------------------------------------------------
# Root endpoints
# ---------------------------------------------------------------------------


@app.get("/", tags=["Health"])
def root() -> dict:
    """Return a simple liveness indicator."""
    return {"message": "FinSolve RAG Chatbot API", "status": "running"}


@app.get("/health", tags=["Health"])
def health() -> dict:
    """Return operational metadata for monitoring."""
    return {"status": "healthy", "ollama_model": settings.OLLAMA_MODEL}
