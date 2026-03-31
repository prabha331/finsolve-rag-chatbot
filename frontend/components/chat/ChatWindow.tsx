"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { v4 as uuidv4 } from "uuid";

import { useAppStore } from "@/lib/store";
import { streamChat } from "@/lib/api";

import MessageBubble    from "@/components/chat/MessageBubble";
import InputBar         from "@/components/chat/InputBar";
import RoleBadge        from "@/components/chat/RoleBadge";
import SuggestedQueries from "@/components/chat/SuggestedQueries";

// ---------------------------------------------------------------------------
// Role descriptions shown in the user info banner
// ---------------------------------------------------------------------------

const ROLE_DESCRIPTIONS: Record<string, string> = {
  employee:    "General Employee — Handbook access",
  hr:          "HR Department — HR data + Handbook",
  finance:     "Finance Department — Finance reports + Handbook",
  marketing:   "Marketing Department — Marketing reports + Handbook",
  engineering: "Engineering Department — Eng docs + Handbook",
  c_level:     "C-Level Executive — Full access",
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ToastState {
  id:      string;
  message: string;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-lg"
    >
      <svg className="h-4 w-4 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
      <span className="flex-1">{message}</span>
      <button
        onClick={onDismiss}
        className="shrink-0 rounded p-0.5 hover:bg-red-100"
        aria-label="Dismiss error"
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ChatWindow() {
  const router = useRouter();

  const {
    token,
    user,
    messages,
    setUser,
    addMessage,
    updateLastMessage,
    clearMessages,
    logout,
  } = useAppStore();

  const [isStreaming, setIsStreaming] = useState(false);
  const [toast, setToast]             = useState<ToastState | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const bottomRef     = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // -------------------------------------------------------------------------
  // Auth guard — verify token on mount, redirect if missing or invalid
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!token) {
      router.replace("/login");
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Unauthorized");
        return res.json();
      })
      .then((data: { email: string; role: string; full_name?: string }) => {
        setUser(data);
        setAuthChecked(true);
      })
      .catch(() => {
        logout();
        router.replace("/login");
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // -------------------------------------------------------------------------
  // Auto-scroll to bottom on new messages or streaming tokens
  // -------------------------------------------------------------------------
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // -------------------------------------------------------------------------
  // Toast helpers
  // -------------------------------------------------------------------------
  const showToast = useCallback((message: string) => {
    const id = uuidv4();
    setToast({ id, message });
    setTimeout(() => setToast((t) => (t?.id === id ? null : t)), 6000);
  }, []);

  // -------------------------------------------------------------------------
  // Send handler
  // -------------------------------------------------------------------------
  const handleSend = useCallback(
    async (query: string) => {
      if (!token || isStreaming) return;

      addMessage({
        id:        uuidv4(),
        role:      "user",
        content:   query,
        timestamp: new Date(),
      });

      const assistantId = uuidv4();
      addMessage({
        id:        assistantId,
        role:      "assistant",
        content:   "",
        timestamp: new Date(),
      });

      setIsStreaming(true);

      const history = messages.map((m) => ({ role: m.role, content: m.content }));

      try {
        await streamChat(
          query,
          history,
          token,
          (tok: string) => updateLastMessage(tok),
          ()           => setIsStreaming(false),
        );
      } catch (err: unknown) {
        setIsStreaming(false);
        const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
        showToast(msg);
        updateLastMessage(`Sorry, I encountered an error: ${msg}`);
      }
    },
    [token, isStreaming, messages, addMessage, updateLastMessage, showToast],
  );

  // -------------------------------------------------------------------------
  // Render — loading screen while auth check runs
  // -------------------------------------------------------------------------
  if (!authChecked) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4 text-slate-500">
          <svg className="h-8 w-8 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span className="text-sm">Verifying session…</span>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // User info banner (shown in empty state)
  // -------------------------------------------------------------------------
  const UserInfoBanner = user ? (
    <div className="mx-auto w-full max-w-2xl rounded-xl border border-blue-100 bg-blue-50 p-4 mb-4">
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white font-bold text-sm shadow-sm">
          {user.email[0].toUpperCase()}
        </div>

        {/* Identity */}
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 truncate">
            {user.full_name || user.email}
          </p>
          <p className="text-sm text-gray-500">
            {ROLE_DESCRIPTIONS[user.role] ?? user.role} •{" "}
            <span className="text-blue-600 font-medium">Verified ✓</span>
          </p>
        </div>
      </div>
    </div>
  ) : null;

  // -------------------------------------------------------------------------
  // Main layout
  // -------------------------------------------------------------------------
  return (
    <div className="flex h-screen flex-col bg-slate-50">

      {/* ------------------------------------------------------------------ */}
      {/* Header                                                              */}
      {/* ------------------------------------------------------------------ */}
      <header className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        {/* Left: logo + title */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 shadow-sm">
            <span className="text-[11px] font-bold text-white">FS</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-900 leading-none">
              FinSolve Assistant
            </h1>
            {user?.email && (
              <p className="mt-0.5 text-[11px] text-slate-400 leading-none">
                {user.email}
              </p>
            )}
          </div>
        </div>

        {/* Right: role badge + actions */}
        <div className="flex items-center gap-3">
          {user?.role && <RoleBadge role={user.role} />}

          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              disabled={isStreaming}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 transition-colors hover:border-slate-300 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              title="Clear conversation"
            >
              Clear
            </button>
          )}

          <button
            onClick={() => { logout(); router.replace("/login"); }}
            disabled={isStreaming}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign out
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Message list                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div
        ref={scrollAreaRef}
        className="flex-1 overflow-y-auto px-4 py-6 sm:px-6"
      >
        {messages.length === 0 ? (
          /* Empty state — user info banner + suggested queries */
          <div className="flex flex-col">
            {UserInfoBanner}
            <SuggestedQueries
              role={user?.role ?? "employee"}
              onSelect={(query) => { if (!isStreaming) handleSend(query); }}
            />
          </div>
        ) : (
          /* Message bubbles */
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {messages.map((msg, idx) => {
              const isLast       = idx === messages.length - 1;
              const bubbleStream = isLast && isStreaming && msg.role === "assistant";
              return (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isStreaming={bubbleStream}
                  userEmail={user?.email}
                />
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Toast                                                               */}
      {/* ------------------------------------------------------------------ */}
      {toast && (
        <div className="pointer-events-auto absolute bottom-28 left-1/2 z-50 w-full max-w-md -translate-x-1/2 px-4">
          <Toast message={toast.message} onDismiss={() => setToast(null)} />
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Input bar                                                           */}
      {/* ------------------------------------------------------------------ */}
      <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-3xl">
          <InputBar onSend={handleSend} isLoading={isStreaming} />
        </div>
      </div>
    </div>
  );
}
