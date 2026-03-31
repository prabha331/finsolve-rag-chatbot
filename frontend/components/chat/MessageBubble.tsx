"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/lib/store";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date instanceof Date ? date : new Date(date));
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function BotAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 shadow-sm">
      <span className="text-[11px] font-bold tracking-tight text-white">FS</span>
    </div>
  );
}

function UserAvatar({ email }: { email?: string }) {
  const initial = email ? email[0].toUpperCase() : "U";
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-700 shadow-sm">
      <span className="text-[11px] font-bold text-white">{initial}</span>
    </div>
  );
}

function StreamingCursor() {
  return (
    <span
      aria-hidden="true"
      className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[1px] animate-pulse rounded-sm bg-slate-500"
    />
  );
}

function SourcePills({ sources }: { sources: string[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="mt-2.5 flex flex-wrap gap-1.5">
      <span className="self-center text-[11px] font-medium text-slate-400">Sources:</span>
      {sources.map((src) => (
        <span
          key={src}
          className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] text-slate-500 transition-colors hover:border-slate-300 hover:bg-slate-100"
        >
          <span aria-hidden="true">📄</span>
          {src}
        </span>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Markdown components
// ---------------------------------------------------------------------------

const MD_COMPONENTS: React.ComponentProps<typeof ReactMarkdown>["components"] = {
  // Paragraphs — source citation lines get a distinct footer style
  p: ({ children }) => {
    const text = String(children);
    if (text.includes("Source:")) {
      return (
        <p className="mt-2 border-t border-slate-100 pt-2 text-xs font-normal not-italic text-slate-500">
          📄 {text.replace("[Source:", "Source:").replace("]", "")}
        </p>
      );
    }
    return <p className="mb-2 leading-relaxed last:mb-0">{children}</p>;
  },
  // Headings
  h1: ({ children }) => (
    <h1 className="mb-2 mt-3 text-base font-bold text-slate-900">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-1.5 mt-3 text-sm font-bold text-slate-900">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-1 mt-2 text-sm font-semibold text-slate-800">{children}</h3>
  ),
  // Lists
  ul: ({ children }) => (
    <ul className="mb-2 ml-4 list-disc space-y-0.5">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 ml-4 list-decimal space-y-0.5">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  // Inline formatting
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-slate-300 pl-3 italic text-slate-600">
      {children}
    </blockquote>
  ),
  // Code — inline vs block distinguished by presence of a language class
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className);
    if (isBlock) {
      return (
        <code
          className={`block overflow-x-auto rounded-md bg-slate-100 p-3 font-mono text-[12px] leading-relaxed text-slate-800 ${className ?? ""}`}
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[12px] text-slate-700"
        {...props}
      >
        {children}
      </code>
    );
  },
  // Code block wrapper
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-md bg-slate-100">{children}</pre>
  ),
  // Links — rendered as plain text; no navigation (source citations must not redirect)
  a: ({ children }) => (
    <span className="font-normal not-italic text-slate-500">{children}</span>
  ),
  // Tables
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-slate-200 bg-slate-50 px-3 py-1.5 text-left text-xs font-semibold text-slate-700">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-slate-200 px-3 py-1.5 text-slate-600">{children}</td>
  ),
  // Horizontal rule
  hr: () => <hr className="my-3 border-slate-200" />,
};

// Access-denied variant — same structure, red palette
const MD_DENIED_COMPONENTS: React.ComponentProps<typeof ReactMarkdown>["components"] = {
  ...MD_COMPONENTS,
  p: ({ children }) => (
    <p className="mb-2 leading-relaxed text-red-800 last:mb-0">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-red-900">{children}</strong>
  ),
  ul: ({ children }) => (
    <ul className="mb-2 ml-4 list-disc space-y-0.5 text-red-700">{children}</ul>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed text-red-700">{children}</li>
  ),
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  userEmail?: string;
}

export default function MessageBubble({
  message,
  isStreaming = false,
  userEmail,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAccessDenied = message.content.startsWith("🔒");

  // --- User bubble ---
  if (isUser) {
    return (
      <div className="flex items-end justify-end gap-2.5">
        <div className="flex min-w-0 max-w-[75%] flex-col items-end gap-1">
          <div className="break-words rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2.5 text-sm text-white shadow-sm">
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          </div>
          <time
            className="text-[11px] text-slate-400"
            dateTime={message.timestamp.toString()}
          >
            {formatTime(message.timestamp)}
          </time>
        </div>
        <UserAvatar email={userEmail} />
      </div>
    );
  }

  // --- Access-denied bubble ---
  if (isAccessDenied) {
    return (
      <div className="flex items-start gap-2.5">
        <BotAvatar />

        <div className="flex min-w-0 max-w-[78%] flex-col gap-1">
          <div className="break-words rounded-2xl rounded-tl-sm border border-red-200 bg-red-50 px-4 py-3 text-sm shadow-sm">
            {/* Lock header */}
            <div className="mb-2 flex items-center gap-2">
              <span className="text-lg text-red-500" aria-hidden="true">🔒</span>
              <span className="text-sm font-semibold text-red-700">Access Restricted</span>
            </div>

            {/* Markdown body — strip the leading emoji since it's in the header */}
            <div className="min-h-[1.4em]">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={MD_DENIED_COMPONENTS}
              >
                {message.content.replace(/^🔒\s*/, "")}
              </ReactMarkdown>
              {isStreaming && <StreamingCursor />}
            </div>
          </div>

          {!isStreaming && (
            <time
              className="text-[11px] text-slate-400"
              dateTime={message.timestamp.toString()}
            >
              {formatTime(message.timestamp)}
            </time>
          )}
        </div>
      </div>
    );
  }

  // --- Normal assistant bubble ---
  return (
    <div className="flex items-start gap-2.5">
      <BotAvatar />

      <div className="flex min-w-0 max-w-[78%] flex-col gap-1">
        <div className="break-words rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 shadow-sm">
          <div className="min-h-[1.4em]">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
              {message.content}
            </ReactMarkdown>
            {isStreaming && <StreamingCursor />}
          </div>

          {!isStreaming && message.sources && message.sources.length > 0 && (
            <SourcePills sources={message.sources} />
          )}
        </div>

        {!isStreaming && (
          <time
            className="text-[11px] text-slate-400"
            dateTime={message.timestamp.toString()}
          >
            {formatTime(message.timestamp)}
          </time>
        )}
      </div>
    </div>
  );
}
