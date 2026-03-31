# FinSolve RAG Chatbot

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-llama3.2-FF6C37?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.6-FF5A1F?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

An internal AI chatbot for **FinSolve Technologies** that answers employee questions using company documents — with strict **Role-Based Access Control (RBAC)** so each user only sees information their role is permitted to access. Built on a fully local stack: no cloud APIs, no data leaves the machine.

---

## Demo

> 📹 _Demo GIF coming soon — record with [LICEcap](https://www.cockos.com/licecap/) or [Kap](https://getkap.co/)_

```
┌─────────────────────────────────────────────────────┐
│  [ Login as Alice — Finance role ]                  │
│  Query: "What was net income in Q3 2024?"           │
│  → Streams answer from quarterly_financial_report   │
│                                                     │
│  [ Login as Eve — Employee role ]                   │
│  Query: "What was net income in Q3 2024?"           │
│  → "I don't have access to that information         │
│     based on your role."                            │
└─────────────────────────────────────────────────────┘
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User's Browser                               │
│                      Next.js 14 Frontend                            │
│         Login Page ──► Chat UI (SSE streaming tokens)               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                │
│                                                                     │
│  POST /auth/login          POST /api/chat                           │
│       │                         │                                   │
│       ▼                         ▼                                   │
│  ┌─────────┐          ┌──────────────────┐                         │
│  │  JWT    │          │  RBAC Service    │  get_allowed_sources()  │
│  │  Issue  │          │  role → [depts]  │                         │
│  └─────────┘          └────────┬─────────┘                         │
│                                │ allowed_sources list               │
│                                ▼                                    │
│                    ┌───────────────────────┐                        │
│                    │   Embedding Service   │  sentence-transformers │
│                    │   embed_text(query)   │                        │
│                    └───────────┬───────────┘                        │
│                                │ query vector                       │
│                                ▼                                    │
│                    ┌───────────────────────┐                        │
│                    │      ChromaDB         │                        │
│                    │  WHERE department     │  RBAC enforced HERE    │
│                    │    IN [allowed_depts] │  at the DB level       │
│                    └───────────┬───────────┘                        │
│                                │ top-k chunks                       │
│                                ▼                                    │
│                    ┌───────────────────────┐                        │
│                    │    LLM Service        │                        │
│                    │  build_prompt()       │                        │
│                    │  stream_response()    │                        │
│                    └───────────┬───────────┘                        │
│                                │ POST /api/chat (stream: true)      │
│                                ▼                                    │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────┐
              │     Ollama  (runs on HOST)        │
              │     llama3.2  (local LLM)         │
              │     No GPU required (CPU mode)    │
              └──────────────────────────────────┘


Ingestion Pipeline (run once before first use):

  data/
  ├── engineering/   ──►  TextLoader / UnstructuredMarkdownLoader
  ├── finance/       ──►  TextLoader
  ├── hr/            ──►  TextLoader + CSVLoader
  └── marketing/     ──►  TextLoader
           │
           ▼  RecursiveCharacterTextSplitter (800 chars, 150 overlap)
           │
           ▼  SentenceTransformer embeddings
           │
           ▼  ChromaDB upsert  {department: "<dept>", source: "<file>"}
```

---

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Backend runtime |
| **FastAPI** | 0.115.6 | REST API + SSE streaming |
| **Uvicorn** | 0.34.0 | ASGI server |
| **ChromaDB** | 0.6.3 | Local vector store with metadata filtering |
| **LangChain** | 0.3.14 | Document loaders and text splitting |
| **sentence-transformers** | 3.3.1 | Local embedding model (no API key needed) |
| **Ollama** | latest | Local LLM runtime (llama3.2) |
| **python-jose** | 3.3.0 | JWT creation and verification |
| **passlib + bcrypt** | 1.7.4 | Password hashing |
| **pydantic-settings** | 2.7.0 | Environment-based configuration |
| **Next.js** | 14.x | React frontend (App Router) |
| **Zustand** | latest | Client-side state (auth + messages) |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **shadcn/ui** | latest | Accessible component primitives |
| **sonner** | latest | Toast notifications |
| **react-markdown** | latest | Markdown rendering in chat bubbles |
| **Docker Compose** | 3.x | Multi-service orchestration |

---

## Role Definitions

| Role | Who | Documents Accessible |
|---|---|---|
| `employee` | General staff | Employee Handbook |
| `hr` | HR department | Employee Handbook, HR Records |
| `finance` | Finance team | Employee Handbook, Finance Reports |
| `marketing` | Marketing team | Employee Handbook, Marketing Reports |
| `engineering` | Engineering team | Employee Handbook, Engineering Docs |
| `c_level` | Executives | **All documents** (all 5 departments) |

> **How RBAC works:** The role is embedded in the JWT at login. At query time, the backend resolves `role → [allowed_departments]` and passes this list as a ChromaDB `WHERE department IN [...]` filter. Unauthorized documents are excluded **before** the similarity search — they are structurally inaccessible, not just hidden.

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Ollama | latest | `ollama --version` |
| Git | any | `git --version` |

---

## Ollama Setup

Ollama runs the LLM **on your host machine** (not in Docker) so it can access your CPU/GPU directly.

**1. Install Ollama**

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download the installer from: https://ollama.ai/download
```

**2. Pull the model**

```bash
ollama pull llama3.2
```

> `llama3.2` is ~2 GB. A smaller alternative is `llama3.2:1b` (~900 MB); update `OLLAMA_MODEL` in `.env` if you switch.

**3. Verify Ollama is working**

```bash
ollama run llama3.2 "hello"
# Expected: some greeting response
# Then: Ctrl+D to exit
```

**4. Start the Ollama server** (if not already running as a service)

```bash
ollama serve
# Listens at http://localhost:11434
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/finsolve-rag-chatbot.git
cd finsolve-rag-chatbot
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set your JWT secret:

```env
JWT_SECRET_KEY=change-this-to-a-long-random-string-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
CHROMA_PERSIST_DIR=./chroma_db
FRONTEND_URL=http://localhost:3000
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

> Generate a strong secret: `python -c "import secrets; print(secrets.token_hex(32))"`

### 3. Set up the Python backend

```bash
cd backend
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Place your documents

Copy your source documents into the `data/` subfolders:

```
data/
├── engineering/   → engineering_master_doc.md
├── finance/       → financial_summary.md, quarterly_financial_report.md
├── hr/            → hr_data.csv, employee_handbook.md
└── marketing/     → marketing_report_2024.md, marketing_report_q*.md
```

### 5. Ingest documents into ChromaDB

```bash
# From the backend/ directory, with .venv activated
python scripts/ingest.py
```

Expected output:
```
============================================================
  FinSolve Document Ingestion Pipeline
============================================================

🗑️  Clearing existing ChromaDB collection...
   New collection created.

📂  employee_handbook (all roles)
    📄  employee_handbook.md: 1 doc(s) → 18 chunks

📂  engineering
    📄  engineering_master_doc.md: 1 doc(s) → 24 chunks
...
✅  Ingestion complete — 142 chunks stored in ChromaDB.
============================================================
```

### 6. Set up the Next.js frontend

```bash
cd ../frontend
npm install
```

---

## Running the App

Open **three terminals**:

**Terminal 1 — Ollama** (skip if already running as a service)
```bash
ollama serve
```

**Terminal 2 — FastAPI backend**
```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 — Next.js frontend**
```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Running with Docker Compose

```bash
# Build and start both services
docker compose up --build

# First run: ingest documents (backend service must be healthy)
docker compose run --rm backend python scripts/ingest.py

# Stop everything
docker compose down
```

> **Docker note:** Ollama must still run on the host. The containers reach it via `host.docker.internal:11434`.

---

## Document Ingestion

The ingestion script (`backend/scripts/ingest.py`) performs a **full re-ingest** every time it runs — the existing ChromaDB collection is deleted and rebuilt. This ensures no stale chunks persist after a document update.

```bash
# Re-ingest after updating documents
python scripts/ingest.py
```

**What happens during ingestion:**

1. Deletes the existing `finsolve_docs` ChromaDB collection
2. Loads each file using the appropriate LangChain loader:
   - `.md` / `.txt` → `UnstructuredMarkdownLoader` (falls back to `TextLoader`)
   - `.csv` → `CSVLoader`
   - `.docx` → `Docx2txtLoader`
3. Splits text into 800-character chunks with 150-character overlap
4. Attaches metadata: `{ department, source, chunk_id }`
5. Embeds all chunks in a single batched sentence-transformer call
6. Upserts into ChromaDB with `ids` for idempotency

**Metadata schema:**

```json
{
  "department": "finance",
  "source": "quarterly_financial_report.md",
  "chunk_id": "3f8a2c1d-..."
}
```

> `employee_handbook.md` is tagged with `department: "employee_handbook"` (not `"hr"`) so all roles can access it via the RBAC filter.

---

## Usage Examples

Log in at [http://localhost:3000/login](http://localhost:3000/login). Use the **Quick Demo Login** buttons or enter credentials manually (password: `password123`).

| User | Role | Example Query | Expected Behaviour |
|---|---|---|---|
| alice@finsolve.com | Finance | _"What was net income in Q3 2024?"_ | Answers from `quarterly_financial_report.md` with source citation |
| bob@finsolve.com | Engineering | _"What does our CI/CD pipeline look like?"_ | Answers from `engineering_master_doc.md` |
| carol@finsolve.com | HR | _"What is the average salary by department?"_ | Answers from `hr_data.csv` |
| david@finsolve.com | Marketing | _"Which campaign had the highest ROI?"_ | Answers from marketing reports |
| eve@finsolve.com | Employee | _"What was net income in Q3 2024?"_ | _"I don't have access to that information based on your role."_ |
| frank@finsolve.com | C-Level | _"Give me a Q4 executive summary"_ | Cross-department answer citing finance + marketing sources |

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/` | None | Liveness check |
| `GET` | `/health` | None | Returns status + configured Ollama model |
| `POST` | `/auth/login` | None | Exchange credentials for JWT. Body: `{email, password}` |
| `GET` | `/auth/me` | Bearer JWT | Returns `{email, role}` of the current token holder |
| `POST` | `/api/chat` | Bearer JWT | Stream RAG response as SSE. Body: `{query, history[]}` |

**POST /auth/login — Request**
```json
{
  "email": "alice@finsolve.com",
  "password": "password123"
}
```

**POST /auth/login — Response**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "role": "finance",
  "email": "alice@finsolve.com"
}
```

**POST /api/chat — Request**
```json
{
  "query": "What was the Q3 net income?",
  "history": [
    { "role": "user",      "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ]
}
```

**POST /api/chat — SSE Response**
```
data: The

data:  Q3

data:  net income

data:  was $2.1M

data:  (Source: quarterly_financial_report.md)

data: [DONE]
```

---

## Project Structure

```
finsolve-rag-chatbot/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # pydantic-settings: loads .env
│   │   │   ├── security.py        # JWT create + verify
│   │   │   └── dependencies.py    # FastAPI get_current_user dependency
│   │   ├── db/
│   │   │   └── users.py           # In-memory user store (demo)
│   │   ├── models/                # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── auth.py            # POST /auth/login, GET /auth/me
│   │   │   └── chat.py            # POST /api/chat (SSE)
│   │   └── services/
│   │       ├── rbac_service.py    # Role → allowed_sources mapping
│   │       ├── vector_service.py  # ChromaDB: add + query with RBAC filter
│   │       ├── embed_service.py   # sentence-transformers embedding
│   │       └── llm_service.py     # Ollama streaming via httpx
│   ├── scripts/
│   │   └── ingest.py              # Document ingestion pipeline
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_rbac.py
│   │   ├── test_chat.py
│   │   └── integration_test.py    # Standalone end-to-end script
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/page.tsx  # Login page
│   │   ├── (chat)/chat/page.tsx   # Chat page
│   │   ├── layout.tsx             # Root layout + Providers
│   │   └── page.tsx               # Root redirect (/ → /chat or /login)
│   ├── components/
│   │   ├── auth/
│   │   │   └── LoginForm.tsx      # Credentials form + quick-login panel
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx     # Main chat container (auth + stream logic)
│   │   │   ├── MessageBubble.tsx  # User/assistant bubbles with markdown
│   │   │   ├── InputBar.tsx       # Auto-resize textarea + send button
│   │   │   ├── RoleBadge.tsx      # Colour-coded role pill with tooltip
│   │   │   └── SuggestedQueries.tsx # Empty-state query suggestions
│   │   └── Providers.tsx          # QueryClient + Toaster
│   ├── hooks/
│   │   └── useAuth.ts             # Auth state + logout helper
│   ├── lib/
│   │   ├── api.ts                 # login() + streamChat() fetch wrappers
│   │   └── store.ts               # Zustand: token, user, messages
│   ├── Dockerfile
│   └── next.config.mjs
│
├── data/
│   ├── engineering/
│   ├── finance/
│   ├── hr/
│   ├── marketing/
│   └── metadata.json              # Department → roles mapping reference
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Key Architecture Decisions

### Why RAG instead of fine-tuning?

Fine-tuning a model on company documents is expensive (compute + time), requires retraining whenever documents change, and can cause the model to "forget" general reasoning. RAG retrieves the relevant document chunks at query time — document updates require only re-ingestion, not retraining. It also provides **verifiable citations** (the `source` metadata) which fine-tuning cannot.

### Why ChromaDB?

ChromaDB runs fully in-process with zero infrastructure — no separate database server to manage. Its `where` metadata filter is applied at the HNSW index level, meaning RBAC is enforced structurally before similarity ranking. Unauthorized documents are excluded from the candidate set entirely, not filtered out after retrieval.

### Why Ollama?

All inference runs locally — no API keys, no usage costs, no data sent to third-party servers. This is critical for an internal tool handling potentially sensitive financial, HR, and engineering data. Ollama also provides a simple OpenAI-compatible HTTP API, making it easy to swap models (`llama3.2`, `mistral`, `gemma2`, etc.) by changing a single `.env` variable.

### Why FastAPI?

FastAPI's `EventSourceResponse` (via `sse-starlette`) streams tokens from Ollama directly to the browser with minimal buffering. Its native `async`/`await` support means a single worker can handle many concurrent SSE connections without blocking. Pydantic models provide automatic request validation and clear API documentation via the auto-generated `/docs` Swagger UI.

### Why sentence-transformers for embeddings?

The `all-MiniLM-L6-v2` model (sentence-transformers' default) runs entirely locally, produces 384-dimensional embeddings in ~10ms per batch, and has strong performance on semantic similarity tasks. No embedding API key or network call is needed, consistent with the "no data leaves the machine" design principle.

---

## Adding New Roles / Documents

### Add a new role

**1. Add the role to `backend/app/services/rbac_service.py`:**
```python
ROLE_PERMISSIONS: dict[str, list[str]] = {
    # ... existing roles ...
    "legal": ["employee_handbook", "legal"],   # ← new role
}
```

**2. Add the user to `backend/app/db/users.py`:**
```python
"grace@finsolve.com": {
    "email": "grace@finsolve.com",
    "hashed_password": _HASHED_DEMO_PASSWORD,
    "role": "legal",
    "full_name": "Grace Hopper",
},
```

**3. Create the document folder and add documents:**
```bash
mkdir data/legal
cp your-legal-docs.md data/legal/
```

**4. Update the ingestion mapping in `backend/scripts/ingest.py`:**
```python
DEPARTMENT_FOLDERS: dict[str, Path] = {
    # ... existing entries ...
    "legal": _DATA_DIR / "legal",
}
```

**5. Re-ingest:**
```bash
python scripts/ingest.py
```

**6. Update the frontend role badge in `frontend/components/chat/RoleBadge.tsx`:**
```typescript
legal: {
  label: "Legal",
  badge: "border-rose-300 bg-rose-100 text-rose-800 hover:bg-rose-200",
  tooltip: "bg-rose-900 text-rose-100",
  access: "Employee Handbook, Legal Documents",
},
```

**7. Add suggested queries in `frontend/components/chat/SuggestedQueries.tsx`.**

### Add documents to an existing department

1. Drop the file into the appropriate `data/<department>/` folder.
2. Re-run `python scripts/ingest.py` — the full collection is rebuilt.
3. No code changes needed.

---

## Troubleshooting

### Ollama is not running / connection refused

**Symptom:** Chat returns `[ERROR] Could not connect to the local LLM.`

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start it
ollama serve

# Verify the model is pulled
ollama list
# Should show: llama3.2
```

### ChromaDB errors on startup

**Symptom:** `Collection 'finsolve_docs' does not exist` or empty responses.

```bash
# Re-run ingestion
cd backend
python scripts/ingest.py

# If the DB is corrupted, delete and rebuild
rm -rf ../chroma_db
python scripts/ingest.py
```

### CORS errors in the browser console

**Symptom:** `Access-Control-Allow-Origin` errors in DevTools.

- Ensure `FRONTEND_URL` in `.env` matches exactly where the frontend is running (e.g., `http://localhost:3000`).
- Restart the backend after changing `.env`.
- Check that `allow_credentials=True` is set alongside explicit origins in `app/main.py`.

### JWT errors / 401 on every request

**Symptom:** All API calls return 401 after login.

- Ensure `JWT_SECRET_KEY` in `.env` is set and non-empty.
- Check system clocks: large clock skew between client and server can cause tokens to appear expired.
- Clear browser `localStorage` and log in again: `localStorage.clear()`.

### Model responses are very slow

- llama3.2 (3B parameters) requires ~4 GB RAM. Ensure no other memory-intensive processes are running.
- Try the smaller `llama3.2:1b` model:
  ```bash
  ollama pull llama3.2:1b
  # Update .env:
  OLLAMA_MODEL=llama3.2:1b
  ```

### `sentence-transformers` download on first run

The embedding model (~90 MB) is downloaded from HuggingFace on first use and cached at `~/.cache/huggingface/`. Subsequent runs use the cache. Ensure internet access on first startup, then it works fully offline.

### Docker: `host.docker.internal` not resolving on Linux

Add to your `.env` (or the `backend` service environment in `docker-compose.yml`):
```env
OLLAMA_BASE_URL=http://172.17.0.1:11434
```
`172.17.0.1` is the default Docker bridge gateway on Linux. Run `ip route | grep default` to confirm your host's address.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">Built for FinSolve Technologies · Internal use only</p>
