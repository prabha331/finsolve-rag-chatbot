"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import LoginForm from "@/components/auth/LoginForm";

export default function LoginPage() {
  const router = useRouter();
  const token  = useAppStore((s) => s.token);

  // If already authenticated, skip the login screen entirely.
  useEffect(() => {
    if (token) router.replace("/chat");
  }, [token, router]);

  // Don't flash the login UI while the redirect is in flight.
  if (token) return null;

  return (
    <div className="flex min-h-screen">
      {/* ------------------------------------------------------------------ */}
      {/* Left panel — branding                                               */}
      {/* ------------------------------------------------------------------ */}
      <aside className="relative hidden w-[46%] flex-col justify-between overflow-hidden bg-slate-900 p-12 lg:flex">
        {/* Grid texture */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        {/* Accent orbs */}
        <div className="pointer-events-none absolute -top-32 -right-32 h-[480px] w-[480px] rounded-full bg-gradient-to-br from-blue-600/30 to-violet-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-24 h-[360px] w-[360px] rounded-full bg-gradient-to-tr from-slate-700/60 to-blue-800/20 blur-3xl" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 shadow-lg shadow-blue-900/40">
            <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span className="text-xl font-bold tracking-tight text-white">FinSolve</span>
        </div>

        {/* Hero copy */}
        <div className="relative z-10 space-y-6">
          <div className="space-y-3">
            <h1 className="text-4xl font-bold leading-tight tracking-tight text-white">
              Your intelligent<br />internal assistant
            </h1>
            <p className="max-w-xs text-base leading-relaxed text-slate-400">
              Securely search company documents, reports, and policies — filtered
              to exactly what your role can access.
            </p>
          </div>
          <div className="flex flex-col gap-2.5">
            {[
              { icon: "🔒", label: "Role-based document access" },
              { icon: "⚡", label: "Instant answers from internal data" },
              { icon: "🤖", label: "Powered by local AI — no cloud exposure" },
            ].map(({ icon, label }) => (
              <div
                key={label}
                className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-slate-300 backdrop-blur-sm"
              >
                <span>{icon}</span>
                {label}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10">
          <p className="text-xs text-slate-600">
            © {new Date().getFullYear()} FinSolve Technologies. Internal use only.
          </p>
        </div>
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* Right panel — form                                                  */}
      {/* ------------------------------------------------------------------ */}
      <main className="flex flex-1 flex-col items-center justify-center bg-slate-50 px-6 py-12">
        {/* Mobile logo */}
        <div className="mb-10 flex items-center gap-3 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-700">
            <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">FinSolve</span>
        </div>
        <LoginForm />
      </main>
    </div>
  );
}
