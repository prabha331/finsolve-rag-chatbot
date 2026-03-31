/**
 * API client for the FinSolve RAG Chatbot backend.
 *
 * `register`   — registers a new user account (always employee role).
 * `login`      — exchanges credentials for a JWT via POST /auth/login.
 * `streamChat` — sends a chat query and consumes the SSE stream token by token.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  email: string;
  full_name: string;
  is_approved: boolean;
}

export interface RegisterResponse {
  message:     string;
  email:       string;
  role:        string;
  is_approved: boolean;
  verified:    boolean;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

// ---------------------------------------------------------------------------
// register
// ---------------------------------------------------------------------------

/**
 * Register a new account with HR verification.
 *
 * Throws an error that carries `error.response = { status, data }` so the
 * caller can read `error.response.data.detail` — the same shape axios uses —
 * without adding axios as a dependency.
 *
 * @throws structured error with `.response.data.detail` on non-2xx responses.
 * @throws plain TypeError on network failure (no `.response` attached).
 */
export async function register(
  email:              string,
  password:           string,
  confirm_password:   string,
  full_name:          string,
  employee_id:        string,
  claimed_department: string,
): Promise<RegisterResponse> {
  let res: Response;

  try {
    res = await fetch(`${API_URL}/auth/register`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        confirm_password,
        full_name,
        employee_id,
        claimed_department,
      }),
    });
  } catch (networkErr) {
    // fetch itself threw — server unreachable, CORS preflight failed, etc.
    console.error("[REGISTER] Network error:", networkErr);
    throw networkErr;           // no .response attached → LoginForm shows "Cannot connect"
  }

  const body = await res.json().catch(() => ({}));

  console.error("[REGISTER]", { status: res.status, body });

  if (!res.ok) {
    // Attach the response shape so LoginForm can read error.response?.data?.detail
    const err: any = new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Registration failed (${res.status})`
    );
    err.response = { status: res.status, data: body };
    throw err;
  }

  return body as RegisterResponse;
}

// ---------------------------------------------------------------------------
// login
// ---------------------------------------------------------------------------

/**
 * Authenticate a user and return the JWT access token + identity.
 *
 * @throws {Error} If the server returns a non-2xx status (e.g. 401, 403).
 */
export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Login failed (${res.status})`);
  }

  return res.json() as Promise<LoginResponse>;
}

// ---------------------------------------------------------------------------
// streamChat
// ---------------------------------------------------------------------------

/**
 * Send a chat query to the backend and stream the response token by token.
 *
 * Opens a `fetch` request with a `ReadableStream` body, reads the SSE
 * line-by-line, and calls `onToken` for each text token received.
 * Calls `onDone` when the `[DONE]` sentinel is encountered or the stream ends.
 *
 * @param query    The user's current question.
 * @param history  Prior conversation turns (sent for multi-turn context).
 * @param token    JWT access token from the login response.
 * @param onToken  Called with each text token as it arrives.
 * @param onDone   Called once when the stream is fully consumed.
 *
 * @throws {Error} If the server returns a non-2xx status before streaming begins.
 */
export async function streamChat(
  query: string,
  history: HistoryMessage[],
  token: string,
  onToken: (t: string) => void,
  onDone: () => void
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query, history }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Chat request failed (${res.status})`);
  }

  if (!res.body) {
    throw new Error("Response body is null — SSE stream unavailable.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;

        const raw = trimmed.slice("data:".length);
        const data = raw.startsWith(" ") ? raw.slice(1) : raw;

        if (data === "[DONE]") {
          onDone();
          return;
        }

        if (data) {
          try {
            onToken(JSON.parse(data) as string);
          } catch {
            onToken(data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  onDone();
}
