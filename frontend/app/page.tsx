"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";

/**
 * Root route — immediately redirects to /chat if authenticated, else /login.
 * Renders nothing visible; the redirect fires before paint.
 */
export default function RootPage() {
  const router = useRouter();
  const token  = useAppStore((s) => s.token);

  useEffect(() => {
    router.replace(token ? "/chat" : "/login");
  }, [token, router]);

  return null;
}
