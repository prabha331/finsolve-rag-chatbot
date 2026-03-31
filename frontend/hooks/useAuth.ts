"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import type { User } from "@/lib/store";

interface UseAuthReturn {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  logout: () => void;
}

/**
 * Convenience hook for auth state and actions.
 *
 * Reads from the Zustand store so components don't need to import the store
 * directly.  `logout` clears the store and navigates to /login.
 */
export function useAuth(): UseAuthReturn {
  const router          = useRouter();
  const token           = useAppStore((s) => s.token);
  const user            = useAppStore((s) => s.user);
  const storeLogout     = useAppStore((s) => s.logout);

  const logout = useCallback(() => {
    storeLogout();
    router.replace("/login");
  }, [storeLogout, router]);

  return {
    user,
    token,
    isAuthenticated: !!token,
    logout,
  };
}
