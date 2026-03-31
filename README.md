# FinSolve Assistant — RAG Chatbot with Role-Based Access Control

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![Groq](https://img.shields.io/badge/Groq-LLaMA3-orange)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.6.3-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

An internal AI chatbot for FinSolve Technologies that answers employee questions using company documents — with strict Role-Based Access Control (RBAC) so each user only sees information their role is permitted to access.

Built with FastAPI + Next.js + ChromaDB + Groq (LLaMA3) — fast, free, and fully cloud-deployable.

---

## Demo
```
[ Login as Alice — Finance role ]
Query: "What was net income in Q3 2024?"
→ Streams answer from quarterly_financial_report.md

[ Login as Eve — Employee role ]
Query: "What was net income in Q3 2024?"
→ "I don't have access to that information based on your role."

[ Login as Bob — Engineering role ]
Query: "How many employees resigned?"
→ "Access Denied — HR data requires HR role or C-Level access."
```

---

## Architecture Overview
```
┌─────────────────────────────────────────────────┐
│              User's Browser                     │
│           Next.js 14 Frontend                   │
│    Login Page ──► Chat UI (SSE streaming)       │
└─────────────────────┬───────────────────────────┘
                      │ HTTP / SSE
                      ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend                    │
│                                                 │
│  /auth/login    /auth/register    /api/chat     │
│       │                               │         │
│       ▼                               ▼         │
│  SQLite DB                      RBAC Service    │
│  (users table)                role→[depts]      │
│       │                               │         │
│       ▼                               ▼         │
│  JWT Token                    Embed Service     │
│  (role claim)              sentence-transformers│
│                                       │         │
│                                       ▼         │
│                               ChromaDB          │
│                         WHERE dept IN [allowed] │
│                         ← RBAC enforced HERE    │
│                                       │         │
│                                       ▼         │
│                              LLM Service        │
│                           build_prompt()        │
│                           stream_response()     │
└───────────────────────────────────┬─────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │       Groq Cloud API      │
                    │   llama-3.1-8b-instant    │
                    │   Fast inference, free    │
                    └───────────────────────────┘
```

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Backend runtime |
| FastAPI | 0.115.6 | REST API + SSE streaming |
| Uvicorn | 0.34.0 | ASGI server |
| SQLAlchemy | 2.x | SQLite ORM for user management |
| ChromaDB | 0.6.3 | Vector store with metadata filtering |
| LangChain | 0.3.14 | Document loaders and text splitting |
| sentence-transformers | 3.3.1 | Local embedding model |
| Groq API | latest | Cloud LLM — llama-3.1-8b-instant |
| python-jose | 3.3.0 | JWT creation and verification |
| passlib + bcrypt | 1.7.4 | Password hashing |
| pydantic-settings | 2.7.0 | Environment-based configuration |
| Next.js | 14.x | React frontend (App Router) |
| Zustand | latest | Client-side state management |
| Tailwind CSS | 3.x | Utility-first styling |
| shadcn/ui | latest | Accessible component primitives |
| react-markdown | latest | Markdown rendering in chat |

---

## Role Definitions

| Role | Who | Documents Accessible |
|------|-----|---------------------|
| employee | All general staff | Employee Handbook only |
| hr | HR department | Employee Handbook + HR Records |
| finance | Finance team | Employee Handbook + Finance Reports |
| marketing | Marketing team | Employee Handbook + Marketing Reports |
| engineering | Engineering team | Employee Handbook + Engineering Docs |
| c_level | Executives | ALL documents (full access) |

**How RBAC works:** The role is embedded in the JWT at login. At query time the backend resolves `role → [allowed_departments]` and passes this as a ChromaDB `WHERE department IN [...]` filter. Unauthorized documents are excluded **before** similarity search — they are structurally inaccessible, not just hidden in the UI.

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |
| Groq API Key | free | https://console.groq.com |

---

## Get Your Free Groq API Key

1. Go to **https://console.groq.com**
2. Sign up free (GitHub login works)
3. Click **API Keys → Create API Key**
4. Copy the key — looks like `gsk_xxxxxxxxxxxxxxxxxxxx`

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/prabha331/finsolve-rag-chatbot.git
cd finsolve-rag-chatbot
```

### 2. Configure environment variables
```bash
cd backend
cp .env.example .env
```

Edit `.env` and fill in your values:
```env
JWT_SECRET_KEY=your-random-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
CHROMA_PERSIST_DIR=./chroma_db
FRONTEND_URL=http://localhost:3000
GROQ_API_KEY=gsk_your_groq_key_here
```

Generate a strong JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Set up the Python backend
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Seed the database
```bash
python scripts/seed_db.py
```

This creates the SQLite database and seeds 6 demo users.

### 5. Ingest documents into ChromaDB
```bash
python scripts/ingest.py
```

Expected output:
```
✅ Embedding model loaded: all-MiniLM-L6-v2
📂 employee_handbook → 18 chunks
📂 engineering → 24 chunks
📂 finance → 31 chunks
📂 hr → 42 chunks
📂 marketing → 27 chunks
✅ Ingestion complete — 142 chunks stored in ChromaDB.
```

### 6. Set up the Next.js frontend
```bash
cd ../frontend
npm install
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Running the App

Open **2 terminals:**

**Terminal 1 — FastAPI backend:**
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Next.js frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

> No Ollama needed! Groq runs in the cloud and responds in 1-3 seconds.

---

## Usage Examples

Login at `http://localhost:3000`. Use credentials below (password: `password123`):

| Email | Role | Example Query | Expected |
|-------|------|---------------|----------|
| alice@finsolve.com | Finance | "What was net income in Q3 2024?" | Answer from quarterly report |
| bob@finsolve.com | Engineering | "What does our CI/CD pipeline look like?" | Answer from engineering docs |
| carol@finsolve.com | HR | "What is the average salary by department?" | Answer from hr_data.csv |
| david@finsolve.com | Marketing | "Which campaign had the highest ROI?" | Answer from marketing reports |
| eve@finsolve.com | Employee | "What was net income in Q3 2024?" | Access Denied message |
| frank@finsolve.com | C-Level | "Give me a Q4 executive summary" | Cross-department answer |

---

## Real Employee Registration

Any `@fintechco.com` employee can register with their own password:

1. Click **Register** tab on login page
2. Enter full name, work email, Employee ID, department, password
3. System verifies Employee ID + email against HR records
4. If verified → instant access with correct role
5. If mismatch → clear error showing correct department

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | None | Liveness check |
| GET | `/health` | None | Status + model info |
| POST | `/auth/register` | None | Register new employee |
| POST | `/auth/login` | None | Get JWT token |
| GET | `/auth/me` | Bearer JWT | Current user info |
| POST | `/api/chat` | Bearer JWT | Stream RAG response (SSE) |
| GET | `/admin/users` | C-Level JWT | List all users |
| PATCH | `/admin/users/{email}/role` | C-Level JWT | Update user role |

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
│   │   │   └── dependencies.py    # get_current_user dependency
│   │   ├── db/
│   │   │   ├── database.py        # SQLAlchemy SQLite setup
│   │   │   ├── models.py          # User model
│   │   │   └── crud.py            # DB operations
│   │   ├── routers/
│   │   │   ├── auth.py            # Login, register, me
│   │   │   ├── chat.py            # POST /api/chat (SSE)
│   │   │   └── admin.py           # User management (c_level only)
│   │   └── services/
│   │       ├── rbac_service.py    # Role → allowed_sources + intent detection
│   │       ├── vector_service.py  # ChromaDB: add + query with RBAC filter
│   │       ├── embed_service.py   # sentence-transformers embeddings
│   │       ├── llm_service.py     # Groq API streaming
│   │       └── hr_verify_service.py # Employee ID verification
│   ├── scripts/
│   │   ├── ingest.py              # Document ingestion pipeline
│   │   └── seed_db.py             # Database seeding
│   ├── data/                      # Source documents
│   │   ├── engineering/
│   │   ├── finance/
│   │   ├── hr/
│   │   └── marketing/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/page.tsx  # Login + Register page
│   │   ├── (chat)/chat/page.tsx   # Chat page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── auth/LoginForm.tsx     # Login + Register form
│   │   └── chat/
│   │       ├── ChatWindow.tsx     # Main chat container
│   │       ├── MessageBubble.tsx  # Message rendering + markdown
│   │       ├── InputBar.tsx       # Query input
│   │       ├── RoleBadge.tsx      # Role display with tooltip
│   │       └── SuggestedQueries.tsx
│   ├── lib/
│   │   ├── api.ts                 # API client functions
│   │   └── store.ts               # Zustand state
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Key Architecture Decisions

**Why Groq instead of Ollama?**
Groq's LPU (Language Processing Unit) inference is 10-20x faster than running Llama locally on CPU. `llama-3.1-8b-instant` responds in 1-3 seconds vs 60-120 seconds on CPU. The free tier is generous enough for development and demos. For truly air-gapped deployments, Ollama is still supported by changing the LLM service.

**Why RAG instead of fine-tuning?**
RAG retrieves relevant document chunks at query time — document updates require only re-ingestion, not retraining. It also provides verifiable source citations which fine-tuning cannot.

**Why ChromaDB?**
Runs fully in-process with zero infrastructure. The `where` metadata filter is applied at the HNSW index level meaning RBAC is enforced structurally before similarity ranking — not as a post-retrieval filter.

**Why SQLite for users?**
Zero-infrastructure persistent storage. Users can register, change passwords, and be role-managed by admins without any external database service.

**Why two-layer RBAC?**
1. Intent detection in `rbac_service.py` blocks obviously restricted queries before hitting ChromaDB
2. ChromaDB `WHERE` filter enforces access at the vector retrieval level
This double protection means even if the intent detection misses a query, the vector store never returns unauthorized chunks.

---

## Adding New Roles or Documents

**Add a new role — 4 steps:**

1. Add to `rbac_service.py` ROLE_PERMISSIONS
2. Add department folder under `data/`
3. Update `ingest.py` DEPARTMENT_CONFIG
4. Re-run `python scripts/ingest.py`

**Add documents to existing department:**

Drop the file into `data/<department>/` and re-run ingestion. No code changes needed.

---

## Troubleshooting

**Groq API errors**
```
Check your GROQ_API_KEY in .env is correct
Verify at: https://console.groq.com
```

**ChromaDB empty responses**
```bash
cd backend
python scripts/ingest.py
```

**CORS errors in browser**
```
Ensure FRONTEND_URL in .env matches exactly where 
the frontend is running (e.g., http://localhost:3000)
Restart backend after changing .env
```

**JWT 401 errors**
```
Ensure JWT_SECRET_KEY is set in .env
Clear browser localStorage and log in again
```

**sentence-transformers slow first start**
The embedding model (~90MB) downloads from HuggingFace on first run and is cached locally. Subsequent starts are instant.

---

## License

MIT — see LICENSE for details.
