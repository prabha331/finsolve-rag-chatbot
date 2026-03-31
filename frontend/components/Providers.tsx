"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

/**
 * Client-side providers wrapping the entire app.
 *
 * - QueryClientProvider: makes React Query available everywhere.
 * - Toaster: renders sonner toast notifications.
 *
 * Kept in a separate "use client" file so layout.tsx can stay a
 * Server Component while still mounting client-only context providers.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  // useState ensures each browser session gets its own QueryClient
  // rather than sharing one across requests in SSR.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60_000, retry: 1 },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-center"
        toastOptions={{
          classNames: {
            toast:        "font-sans text-sm",
            error:        "border-red-200 bg-red-50 text-red-800",
            success:      "border-emerald-200 bg-emerald-50 text-emerald-800",
          },
        }}
      />
    </QueryClientProvider>
  );
}
