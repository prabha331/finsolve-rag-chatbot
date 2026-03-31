/**
 * Global Zustand store for FinSolve RAG Chatbot.
 *
 * Holds authentication state (token + user identity) and the active
 * conversation's message history.  `updateLastMessage` appends streaming
 * tokens to the last assistant message in place so the UI re-renders
 * incrementally as tokens arrive from the SSE stream.
 */

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** Source filenames cited by the assistant, if any. */
  sources?: string[];
  timestamp: Date;
}

export interface User {
  email:      string;
  role:       string;
  full_name?: string;
}

interface AppState {
  // --- Auth ---
  token: string | null;
  user: User | null;

  // --- Conversation ---
  messages: Message[];

  // --- Actions ---
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  addMessage: (message: Message) => void;
  /**
   * Append *content* to the last message in the list.
   * Used to stream tokens into an existing assistant bubble.
   */
  updateLastMessage: (content: string) => void;
  clearMessages: () => void;
  /** Reset auth + conversation state (called on logout). */
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  token: null,
  user: null,
  messages: [],

  // --- Auth actions ---
  setToken: (token) => set({ token }),

  setUser: (user) => set({ user }),

  // --- Message actions ---
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateLastMessage: (content) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      messages[messages.length - 1] = {
        ...last,
        content: last.content + content,
      };
      return { messages };
    }),

  clearMessages: () => set({ messages: [] }),

  logout: () => set({ token: null, user: null, messages: [] }),
}));
