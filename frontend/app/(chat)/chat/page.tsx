import ChatWindow from "@/components/chat/ChatWindow";

export const metadata = {
  title: "Chat — FinSolve Assistant",
  description: "Chat with the FinSolve internal AI assistant",
};

/**
 * Chat page — thin wrapper around ChatWindow.
 * Token verification and /login redirect are handled inside ChatWindow
 * on mount so the auth check always runs with the live Zustand state.
 */
export default function ChatPage() {
  return <ChatWindow />;
}
