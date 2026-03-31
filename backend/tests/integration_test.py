"""
Integration test script for the FinSolve RAG Chatbot API.

NOT a pytest file — run directly:
    python tests/integration_test.py

Requires:
  - Backend running at http://localhost:8000
  - Ollama running at http://localhost:11434 with llama3.2 loaded
  - ChromaDB populated (run scripts/ingest.py first)
"""

import json
import sys
import textwrap
import time
from dataclasses import dataclass, field

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
TIMEOUT  = 120   # seconds — Ollama can be slow on first inference

# ---------------------------------------------------------------------------
# ANSI colours for terminal output
# ---------------------------------------------------------------------------

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def ok(msg: str)   -> str: return f"{GREEN}✓{RESET}  {msg}"
def fail(msg: str) -> str: return f"{RED}✗{RESET}  {msg}"
def info(msg: str) -> str: return f"{CYAN}→{RESET}  {msg}"
def warn(msg: str) -> str: return f"{YELLOW}⚠{RESET}  {msg}"

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class Results:
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        if passed:
            self.passed += 1
            print(ok(name))
        else:
            self.failed += 1
            self.errors.append(f"{name}: {detail}")
            print(fail(f"{name} — {detail}"))

    def summary(self) -> None:
        total = self.passed + self.failed
        print()
        print("=" * 60)
        print(f"{BOLD}Results: {self.passed}/{total} tests passed{RESET}")
        if self.errors:
            print(f"\n{RED}Failures:{RESET}")
            for e in self.errors:
                print(f"  {DIM}•{RESET} {e}")
        print("=" * 60)

results = Results()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login(email: str, password: str = "password123") -> str | None:
    """POST /auth/login and return the access token, or None on failure."""
    try:
        res = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if res.status_code == 200:
            return res.json()["access_token"]
        print(f"  {DIM}Login failed ({res.status_code}): {res.text[:120]}{RESET}")
        return None
    except requests.ConnectionError:
        print(f"  {RED}Cannot reach backend at {BASE_URL}. Is it running?{RESET}")
        sys.exit(1)


def stream_chat(token: str, query: str) -> str:
    """POST /api/chat and consume the SSE stream. Returns the full response text."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Accept":        "text/event-stream",
    }
    body = {"query": query, "history": []}

    full_text = ""
    with requests.post(
        f"{BASE_URL}/api/chat",
        headers=headers,
        json=body,
        stream=True,
        timeout=TIMEOUT,
    ) as res:
        if res.status_code != 200:
            return f"[HTTP {res.status_code}] {res.text[:200]}"

        for raw_line in res.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            if data.startswith("[ERROR]"):
                full_text += data
                break
            full_text += data

    return full_text


def print_response(label: str, text: str, max_width: int = 80) -> None:
    """Pretty-print a truncated response."""
    preview = text[:600] + ("…" if len(text) > 600 else "")
    wrapped = textwrap.fill(preview, width=max_width, initial_indent="    ", subsequent_indent="    ")
    print(f"\n  {DIM}── {label} ──{RESET}")
    print(wrapped)
    print()


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print(DIM + "─" * 60 + RESET)

# ---------------------------------------------------------------------------
# 0. Connectivity check
# ---------------------------------------------------------------------------

section("0 · Connectivity")

try:
    health = requests.get(f"{BASE_URL}/health", timeout=5)
    results.record(
        "GET /health returns 200",
        health.status_code == 200,
        f"status={health.status_code}",
    )
    model = health.json().get("ollama_model", "?")
    print(info(f"Ollama model reported: {model}"))
except requests.ConnectionError:
    print(f"{RED}Cannot reach {BASE_URL}. Start the backend first.{RESET}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 1. Authentication — alice (finance)
# ---------------------------------------------------------------------------

section("1 · Authentication — alice@finsolve.com (finance)")

alice_token = login("alice@finsolve.com")
results.record("Login alice → 200 + token",        alice_token is not None)

# Verify token via /auth/me
if alice_token:
    me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {alice_token}"}, timeout=5)
    results.record("GET /auth/me → role=finance",  me.status_code == 200 and me.json().get("role") == "finance")

# Wrong password
bad = requests.post(f"{BASE_URL}/auth/login", json={"email": "alice@finsolve.com", "password": "wrong"}, timeout=5)
results.record("Wrong password → 401",             bad.status_code == 401)

# ---------------------------------------------------------------------------
# 2. Authentication — eve (employee)
# ---------------------------------------------------------------------------

section("2 · Authentication — eve@finsolve.com (employee)")

eve_token = login("eve@finsolve.com")
results.record("Login eve → 200 + token",          eve_token is not None)

if eve_token:
    me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {eve_token}"}, timeout=5)
    results.record("GET /auth/me → role=employee", me.status_code == 200 and me.json().get("role") == "employee")

# ---------------------------------------------------------------------------
# 3. Chat — alice asks about net income (should have access)
# ---------------------------------------------------------------------------

section("3 · Chat — alice asks a finance question")

FINANCE_QUERY = "What was the net income in Q3 2024?"

if alice_token:
    print(info(f"Query: '{FINANCE_QUERY}'"))
    print(info("Streaming response from Ollama (may take 10–30 s)…"))
    t0 = time.time()
    alice_response = stream_chat(alice_token, FINANCE_QUERY)
    elapsed = time.time() - t0

    has_content   = len(alice_response.strip()) > 20
    not_error     = "[ERROR]" not in alice_response
    not_no_access = "don't have access" not in alice_response.lower()

    results.record("Alice gets a non-empty finance response",            has_content)
    results.record("Response does not contain an error token",           not_error)
    results.record("Response does not say 'don't have access'",          not_no_access)

    print_response(f"Alice's answer ({elapsed:.1f}s)", alice_response)
else:
    print(warn("Skipping — alice token unavailable"))

# ---------------------------------------------------------------------------
# 4. Chat — eve asks the same finance question (no access)
# ---------------------------------------------------------------------------

section("4 · Chat — eve asks the same finance question (employee, no finance access)")

if eve_token:
    print(info(f"Query: '{FINANCE_QUERY}'"))
    print(info("Streaming response…"))
    eve_response = stream_chat(eve_token, FINANCE_QUERY)

    # Eve should NOT get a 401 — the system streams a polite refusal or
    # "no relevant information" message instead.
    is_not_empty       = len(eve_response.strip()) > 5
    no_raw_401         = "[HTTP 401]" not in eve_response

    # The response should indicate limited access or no relevant docs
    signals_no_access = any(phrase in eve_response.lower() for phrase in [
        "don't have access",
        "don't have relevant",
        "not have access",
        "no relevant information",
        "i don't have sufficient",
        "based on your role",
    ])

    results.record("Eve gets a response (not a raw 401)",                is_not_empty and no_raw_401)
    results.record("Eve's response signals restricted/no access",        signals_no_access,
                   "Response did not contain an expected access-restriction phrase")

    print_response("Eve's answer", eve_response)
else:
    print(warn("Skipping — eve token unavailable"))

# ---------------------------------------------------------------------------
# 5. Chat — frank (c_level) asks a cross-department question
# ---------------------------------------------------------------------------

section("5 · Chat — frank@finsolve.com (c_level, all access)")

frank_token = login("frank@finsolve.com")
results.record("Login frank → 200 + token", frank_token is not None)

EXEC_QUERY = "Give me a brief overview of Q4 2024 financial performance and any key engineering milestones."

if frank_token:
    print(info(f"Query: '{EXEC_QUERY}'"))
    print(info("Streaming response from Ollama…"))
    t0 = time.time()
    frank_response = stream_chat(frank_token, EXEC_QUERY)
    elapsed = time.time() - t0

    has_content   = len(frank_response.strip()) > 20
    not_error     = "[ERROR]" not in frank_response
    not_no_access = "don't have access" not in frank_response.lower()

    results.record("Frank gets a non-empty response",                    has_content)
    results.record("Response does not contain an error token",           not_error)
    results.record("C-level response does not say 'don't have access'",  not_no_access)

    print_response(f"Frank's answer ({elapsed:.1f}s)", frank_response)
else:
    print(warn("Skipping — frank token unavailable"))

# ---------------------------------------------------------------------------
# 6. Auth guard — unauthenticated chat request
# ---------------------------------------------------------------------------

section("6 · Auth guard — chat without token")

no_auth = requests.post(
    f"{BASE_URL}/api/chat",
    json={"query": "hello"},
    timeout=5,
)
results.record("POST /api/chat without token → 401", no_auth.status_code == 401)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

results.summary()
sys.exit(0 if results.failed == 0 else 1)
