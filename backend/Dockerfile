# ============================================================
# FinSolve Backend — FastAPI + ChromaDB
# ============================================================
# Ollama runs on the HOST machine and is reached via
# host.docker.internal (set in docker-compose.yml).
# ============================================================

FROM python:3.11-slim

# --- System dependencies ---
# curl: used by the healthcheck
# build-essential + libgomp1: required by sentence-transformers / chromadb native libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (cached layer — only re-runs when requirements change) ---
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# --- Application source ---
COPY . .

# Create directories that are expected at runtime.
# In production these are bind-mounted; the mkdir ensures the container
# starts cleanly even without a volume attached.
RUN mkdir -p /app/chroma_db /app/data

# Non-root user for better security
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# uvicorn is started with:
#   --host 0.0.0.0   → listen on all interfaces (required inside Docker)
#   --workers 1      → single worker; ChromaDB's PersistentClient is not safe
#                      to share across multiple OS processes
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
