"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAppStore } from "@/lib/store";
import { login, register } from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEPARTMENTS = [
  "Engineering", "Technology",
  "Finance", "Risk",
  "HR",
  "Marketing", "Sales", "Business", "Product", "Design",
  "Operations", "Compliance", "Quality Assurance", "Data",
  "General/Other",
];

const ALLOWED_DOMAINS = ["@finsolve.com", "@fintechco.com"];

function isAllowedEmail(email: string) {
  return ALLOWED_DOMAINS.some((d) => email.endsWith(d));
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const INPUT_CLS =
  "h-11 w-full bg-white text-gray-900 border-gray-300 " +
  "placeholder:text-gray-400 focus-visible:border-blue-500 focus-visible:ring-blue-500";

const LABEL_CLS = "block text-sm font-medium text-gray-700";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

function ErrorBanner({ message }: { message: string }) {
  const isPending = message.toLowerCase().includes("pending approval");
  if (isPending) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <p className="font-semibold">Account pending approval</p>
        <p className="mt-0.5">
          Your account is awaiting admin approval. Contact{" "}
          <span className="font-mono font-medium">frank@finsolve.com</span> to get approved.
        </p>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      <svg className="mt-0.5 h-4 w-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
      <span>{message}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function LoginForm() {
  const router = useRouter();
  const { setToken, setUser } = useAppStore();

  const [activeTab, setActiveTab] = useState<"login" | "register">("login");

  // --- Login state ---
  const [loginEmail,    setLoginEmail]    = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginLoading,  setLoginLoading]  = useState(false);
  const [loginError,    setLoginError]    = useState<string | null>(null);

  // --- Register state ---
  const [regFullName,        setRegFullName]        = useState("");
  const [regEmail,           setRegEmail]           = useState("");
  const [regEmployeeId,      setRegEmployeeId]      = useState("");
  const [regPassword,        setRegPassword]        = useState("");
  const [regConfirmPassword, setRegConfirmPassword] = useState("");
  const [regDepartment,      setRegDepartment]      = useState("");
  const [regLoading,         setRegLoading]         = useState(false);
  const [regError,           setRegError]           = useState<string | null>(null);
  const [deptMismatchError,  setDeptMismatchError]  = useState<{
    message: string;
    actual:  string;
    claimed: string;
  } | null>(null);

  // Success state: null = not submitted, "verified" = auto-approved, "pending" = needs review
  const [regResult, setRegResult] = useState<"verified" | "pending" | null>(null);

  // For the auto-switch countdown when verified
  const countdownRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (countdownRef.current) clearTimeout(countdownRef.current);
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Login handler
  // ---------------------------------------------------------------------------

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);

    try {
      const data = await login(loginEmail, loginPassword);
      setToken(data.access_token);
      setUser({ email: data.email, role: data.role });
      router.push("/chat");
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoginLoading(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Register handler
  // ---------------------------------------------------------------------------

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setRegError(null);

    // Client-side validation
    if (!isAllowedEmail(regEmail)) {
      setRegError("Only @finsolve.com or @fintechco.com email addresses are allowed.");
      return;
    }
    if (regPassword.length < 8) {
      setRegError("Password must be at least 8 characters.");
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegError("Passwords do not match.");
      return;
    }
    if (!regEmployeeId.trim()) {
      setRegError("Employee ID is required.");
      return;
    }
    if (!regDepartment) {
      setRegError("Please select your department.");
      return;
    }

    setRegLoading(true);
    try {
      const data = await register(
        regEmail,
        regPassword,
        regConfirmPassword,
        regFullName,
        regEmployeeId.trim(),
        regDepartment,
      );

      // Auto-verified — show success, pre-fill login, auto-switch after 3 s
      setRegResult("verified");
      setLoginEmail(regEmail);
      countdownRef.current = setTimeout(() => {
        setRegResult(null);
        setActiveTab("login");
      }, 3000);
    } catch (error: any) {
      setDeptMismatchError(null);
      setRegError(null);

      console.error("[FORM ERROR]", error);

      // No .response = network failure (server unreachable, CORS, etc.)
      if (!error.response) {
        setRegError(
          "Cannot connect to server. " +
          "Please make sure the backend is running at http://localhost:8000"
        );
        return;
      }

      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      console.log("[ERROR DETAIL]", { status, detail });

      if (!detail) {
        setRegError(`Server error (${status}). Please try again.`);
        return;
      }

      // Plain string error (e.g. FastAPI validation, duplicate email)
      if (typeof detail === "string") {
        setRegError(detail);
        return;
      }

      // Structured object error — dispatch on error code
      if (typeof detail === "object") {
        switch (detail.error) {

          case "employee_id_not_found":
            setRegError(
              "❌ Employee ID not found in our HR records. " +
              "Please double-check your Employee ID " +
              "from your ID card or offer letter."
            );
            break;

          case "email_mismatch":
            setRegError(
              "❌ This email address does not match " +
              "our HR records for your Employee ID. " +
              "Please use your official company email."
            );
            break;

          case "department_mismatch":
            setDeptMismatchError({
              message: detail.message        || "",
              actual:  detail.actual_department  || "",
              claimed: detail.claimed_department || "",
            });
            break;

          case "hr_system_unavailable":
            setRegError(
              "⚠️ HR verification is temporarily " +
              "unavailable. Please try again later."
            );
            break;

          case "verification_failed":
            setRegError(
              "❌ Verification failed. Please check " +
              "your Employee ID, email, and department."
            );
            break;

          default:
            setRegError(
              detail.message ||
              "Registration failed. Please check your details and try again."
            );
        }
        return;
      }

      setRegError("Registration failed. Please try again.");
    } finally {
      setRegLoading(false);
    }
  }

  function switchToRegister() {
    setRegError(null);
    setDeptMismatchError(null);
    setRegResult(null);
    setActiveTab("register");
  }

  function switchToLogin() {
    setLoginError(null);
    setActiveTab("login");
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="w-full max-w-md space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-gray-900">FinSolve Assistant</h2>
        <p className="mt-1 text-sm text-gray-500">Sign in or create a new account</p>
      </div>

      {/* Tabs */}
      <div className="flex rounded-lg border border-gray-200 bg-gray-100 p-1">
        <button
          type="button"
          onClick={switchToLogin}
          className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
            activeTab === "login"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Sign In
        </button>
        <button
          type="button"
          onClick={switchToRegister}
          className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
            activeTab === "register"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Register
        </button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* LOGIN TAB                                                           */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === "login" && (
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="login-email" className={LABEL_CLS}>Email address</label>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@finsolve.com"
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
              disabled={loginLoading}
              className={INPUT_CLS}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="login-password" className={LABEL_CLS}>Password</label>
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              placeholder="••••••••"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              disabled={loginLoading}
              className={INPUT_CLS}
            />
          </div>

          {loginError && <ErrorBanner message={loginError} />}

          <Button
            type="submit"
            disabled={loginLoading}
            className="h-11 w-full bg-gray-900 text-white hover:bg-gray-800 active:bg-gray-950"
          >
            {loginLoading ? <span className="flex items-center gap-2"><Spinner /> Signing in…</span> : "Sign In"}
          </Button>
        </form>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* REGISTER TAB                                                        */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === "register" && (
        <>
          {/* ---- Auto-verified success ---- */}
          {regResult === "verified" && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-5 py-4 space-y-2">
              <p className="text-base font-semibold text-emerald-800">✅ Registration successful!</p>
              <p className="text-sm text-emerald-700">
                Your Employee ID was verified against HR records. You have instant access.
              </p>
              <p className="text-sm text-emerald-700">
                Switching to Sign In in 3 seconds… your email has been pre-filled.
              </p>
              <button
                type="button"
                onClick={() => { setRegResult(null); setActiveTab("login"); }}
                className="text-sm text-emerald-700 underline underline-offset-2 hover:text-emerald-900"
              >
                Sign in now →
              </button>
            </div>
          )}

          {/* ---- Pending approval success ---- */}
          {regResult === "pending" && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-5 py-4 space-y-2">
              <p className="text-base font-semibold text-amber-800">⏳ Registration received</p>
              <p className="text-sm text-amber-700">
                Your Employee ID was not found in our current HR records. An admin will
                review your account shortly.
              </p>
              <p className="text-sm text-amber-700">
                Contact <span className="font-mono font-medium">frank@finsolve.com</span> to
                expedite approval.
              </p>
              <button
                type="button"
                onClick={() => { setRegResult(null); setActiveTab("login"); }}
                className="text-sm text-amber-700 underline underline-offset-2 hover:text-amber-900"
              >
                Back to Sign In
              </button>
            </div>
          )}

          {/* ---- Registration form ---- */}
          {!regResult && (
            <form onSubmit={handleRegister} className="space-y-4">
              {/* How verification works */}
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                <p className="font-semibold">How verification works:</p>
                <ul className="mt-1 space-y-1 text-xs text-blue-700">
                  <li>✓ Your Employee ID is checked against HR records</li>
                  <li>✓ If verified, you get instant access with the correct role</li>
                  <li>✓ Your password is private — only you know it</li>
                  <li>✓ Admins cannot see your password</li>
                </ul>
              </div>

              {/* Full Name */}
              <div className="space-y-2">
                <label htmlFor="reg-fullname" className={LABEL_CLS}>Full Name</label>
                <Input
                  id="reg-fullname"
                  type="text"
                  autoComplete="name"
                  required
                  placeholder="Jane Smith"
                  value={regFullName}
                  onChange={(e) => setRegFullName(e.target.value)}
                  disabled={regLoading}
                  className={INPUT_CLS}
                />
              </div>

              {/* Work Email */}
              <div className="space-y-2">
                <label htmlFor="reg-email" className={LABEL_CLS}>
                  Work Email
                  <span className="ml-1 text-xs font-normal text-gray-400">
                    (@finsolve.com or @fintechco.com)
                  </span>
                </label>
                <Input
                  id="reg-email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="you@fintechco.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  disabled={regLoading}
                  className={INPUT_CLS}
                />
              </div>

              {/* Employee ID */}
              <div className="space-y-1">
                <label htmlFor="reg-empid" className={LABEL_CLS}>Employee ID</label>
                <Input
                  id="reg-empid"
                  type="text"
                  required
                  placeholder="e.g. FINEMP1042 — found on your ID card"
                  value={regEmployeeId}
                  onChange={(e) => setRegEmployeeId(e.target.value)}
                  disabled={regLoading}
                  className={INPUT_CLS}
                />
                <p className="text-xs text-gray-500">
                  Your Employee ID is printed on your company ID card or offer letter.
                </p>
              </div>

              {/* Department */}
              <div className="space-y-2">
                <label htmlFor="reg-department" className={LABEL_CLS}>Department</label>
                <select
                  id="reg-department"
                  required
                  value={regDepartment}
                  onChange={(e) => { setRegDepartment(e.target.value); setDeptMismatchError(null); setRegError(null); }}
                  disabled={regLoading}
                  className="h-11 w-full rounded-md border border-gray-300 bg-white px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="" disabled>Select your department…</option>
                  {DEPARTMENTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>

              {/* Password */}
              <div className="space-y-1">
                <label htmlFor="reg-password" className={LABEL_CLS}>Password</label>
                <Input
                  id="reg-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  placeholder="••••••••"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  disabled={regLoading}
                  className={INPUT_CLS}
                />
                <p className="text-xs text-gray-500">
                  Min 8 characters. Choose something only you know.
                </p>
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <label htmlFor="reg-confirm" className={LABEL_CLS}>Confirm Password</label>
                <Input
                  id="reg-confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                  placeholder="••••••••"
                  value={regConfirmPassword}
                  onChange={(e) => setRegConfirmPassword(e.target.value)}
                  disabled={regLoading}
                  className={INPUT_CLS}
                />
              </div>

              {regError && <ErrorBanner message={regError} />}

              {deptMismatchError && (
                <div className="bg-red-50 border-2 border-red-400 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">⚠️</span>
                    <div className="flex-1">
                      <p className="font-bold text-red-700 text-sm">
                        Wrong Department Selected
                      </p>
                      <p className="text-red-600 text-sm mt-1">
                        Our HR records do not match your selected department.
                      </p>
                      <div className="mt-3 space-y-2">
                        <div className="flex items-center gap-2 bg-white rounded-lg p-2 border border-red-200">
                          <span className="text-red-500 text-xs font-semibold w-24 shrink-0">
                            You selected:
                          </span>
                          <span className="text-red-600 font-bold text-sm">
                            {deptMismatchError.claimed}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 bg-white rounded-lg p-2 border border-green-200">
                          <span className="text-green-600 text-xs font-semibold w-24 shrink-0">
                            Correct dept:
                          </span>
                          <span className="text-green-700 font-bold text-sm">
                            {deptMismatchError.actual}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-red-500 mt-3 font-medium">
                        👆 Please select{" "}
                        <strong className="text-red-700">{deptMismatchError.actual}</strong>{" "}
                        from the Department dropdown above and try again.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <Button
                type="submit"
                disabled={regLoading}
                className="h-11 w-full bg-gray-900 text-white hover:bg-gray-800 active:bg-gray-950"
              >
                {regLoading
                  ? <span className="flex items-center gap-2"><Spinner /> Verifying…</span>
                  : "Create Account"}
              </Button>
            </form>
          )}
        </>
      )}
    </div>
  );
}
