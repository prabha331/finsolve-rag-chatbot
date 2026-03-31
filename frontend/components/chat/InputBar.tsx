"use client";

import { useRef, useState, useCallback } from "react";

const SOFT_LIMIT = 1000;
const MAX_CHARS  = 2000;

interface InputBarProps {
  onSend: (query: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSend, isLoading }: InputBarProps) {
  const [value, setValue]     = useState("");
  const textareaRef           = useRef<HTMLTextAreaElement>(null);

  const charCount    = value.length;
  const overSoft     = charCount >= SOFT_LIMIT;
  const atMax        = charCount >= MAX_CHARS;
  const canSend      = value.trim().length > 0 && !isLoading && !atMax;

  // Grow the textarea to fit content (max ~5 rows ≈ 120 px).
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, []);

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const next = e.target.value.slice(0, MAX_CHARS);
    setValue(next);
    resize();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) submit();
    }
  }

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
    // Reset height after clearing
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  return (
    <div className="w-full space-y-1.5">
      {/* Input card */}
      <div
        className={`
          flex items-end gap-2 rounded-2xl border bg-white px-4 py-3 shadow-sm
          transition-colors
          ${isLoading
            ? "border-slate-200 opacity-80"
            : atMax
            ? "border-red-300 ring-1 ring-red-200"
            : "border-slate-200 focus-within:border-slate-400 focus-within:ring-1 focus-within:ring-slate-300"}
        `}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Ask anything you have access to…"
          aria-label="Chat input"
          className="
            flex-1 resize-none overflow-y-auto bg-transparent text-sm
            leading-relaxed text-slate-800 placeholder:text-slate-400
            focus:outline-none disabled:cursor-not-allowed disabled:text-slate-400
          "
          style={{ minHeight: "24px", maxHeight: "120px" }}
        />

        {/* Character counter */}
        {charCount > 0 && (
          <span
            className={`
              shrink-0 self-end text-[11px] tabular-nums transition-colors
              ${atMax  ? "font-semibold text-red-500"
              : overSoft ? "text-amber-500"
              : "text-slate-400"}
            `}
            aria-live="polite"
          >
            {charCount}/{MAX_CHARS}
          </span>
        )}

        {/* Send button */}
        <button
          type="button"
          onClick={submit}
          disabled={!canSend}
          aria-label="Send message"
          className="
            flex h-8 w-8 shrink-0 items-center justify-center self-end
            rounded-xl bg-blue-600 text-white shadow-sm
            transition-all hover:bg-blue-700 active:scale-95
            disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400
            disabled:shadow-none
          "
        >
          {isLoading ? (
            /* Spinner */
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
          ) : (
            /* Paper-plane icon */
            <svg
              className="h-4 w-4 translate-x-[1px]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>

      {/* Footer hints */}
      <div className="flex items-center justify-between px-1">
        <p className="text-[11px] text-slate-400">
          <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-px font-sans text-[10px] text-slate-500">
            Enter
          </kbd>
          {" "}to send ·{" "}
          <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-px font-sans text-[10px] text-slate-500">
            Shift+Enter
          </kbd>
          {" "}for new line
        </p>

        {atMax && (
          <p className="text-[11px] font-medium text-red-500" role="alert">
            Character limit reached
          </p>
        )}
        {overSoft && !atMax && (
          <p className="text-[11px] text-amber-500">
            {MAX_CHARS - charCount} characters remaining
          </p>
        )}
      </div>
    </div>
  );
}
