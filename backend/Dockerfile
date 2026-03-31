FROM python:3.11-slim

# --- System dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies ---
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# --- HuggingFace FIX (ADD THIS) ---
ENV HF_HOME=/tmp/huggingface
ENV TRANSFORMERS_CACHE=/tmp/huggingface
ENV HUGGINGFACE_HUB_CACHE=/tmp/huggingface

RUN mkdir -p /tmp/huggingface && chmod -R 777 /tmp/huggingface

# --- Application source ---
COPY . .

RUN mkdir -p /app/chroma_db /app/data

# --- Non-root user ---
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
