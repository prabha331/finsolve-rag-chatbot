"use client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RoleConfig {
  label: string;
  icon?: string;
  /** Tailwind classes for the badge itself */
  badge: string;
  /** Tailwind classes for the tooltip */
  tooltip: string;
  /** Human-readable list of accessible data sources */
  access: string;
}

// ---------------------------------------------------------------------------
// Role configuration
// ---------------------------------------------------------------------------

const ROLE_CONFIG: Record<string, RoleConfig> = {
  employee: {
    label: "Employee",
    badge:
      "border-slate-300 bg-slate-100 text-slate-700 hover:bg-slate-200",
    tooltip: "bg-slate-800 text-slate-100",
    access: "Employee Handbook",
  },
  hr: {
    label: "HR",
    badge:
      "border-violet-300 bg-violet-100 text-violet-800 hover:bg-violet-200",
    tooltip: "bg-violet-900 text-violet-100",
    access: "Employee Handbook, HR Records",
  },
  finance: {
    label: "Finance",
    badge:
      "border-emerald-300 bg-emerald-100 text-emerald-800 hover:bg-emerald-200",
    tooltip: "bg-emerald-900 text-emerald-100",
    access: "Employee Handbook, Finance Reports",
  },
  marketing: {
    label: "Marketing",
    badge:
      "border-orange-300 bg-orange-100 text-orange-800 hover:bg-orange-200",
    tooltip: "bg-orange-900 text-orange-100",
    access: "Employee Handbook, Marketing Reports",
  },
  engineering: {
    label: "Engineering",
    badge:
      "border-blue-300 bg-blue-100 text-blue-800 hover:bg-blue-200",
    tooltip: "bg-blue-900 text-blue-100",
    access: "Employee Handbook, Engineering Docs",
  },
  c_level: {
    label: "C-Level Executive",
    icon: "⭐",
    badge:
      "border-amber-400 bg-amber-100 text-amber-900 hover:bg-amber-200 font-semibold",
    tooltip: "bg-amber-900 text-amber-100",
    access: "Employee Handbook, HR Records, Finance Reports, Marketing Reports, Engineering Docs",
  },
};

const FALLBACK: RoleConfig = {
  label: "Unknown",
  badge: "border-slate-200 bg-slate-50 text-slate-500",
  tooltip: "bg-slate-800 text-slate-100",
  access: "No data access configured",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface RoleBadgeProps {
  role: string;
}

export default function RoleBadge({ role }: RoleBadgeProps) {
  const config = ROLE_CONFIG[role] ?? FALLBACK;

  return (
    <div className="group relative inline-flex">
      {/* Badge */}
      <span
        className={`
          inline-flex cursor-default select-none items-center gap-1.5 rounded-full
          border px-2.5 py-0.5 text-xs font-medium transition-colors
          ${config.badge}
        `}
      >
        {config.icon && (
          <span className="text-[10px] leading-none" aria-hidden="true">
            {config.icon}
          </span>
        )}
        {config.label}
      </span>

      {/* Tooltip */}
      <div
        role="tooltip"
        className={`
          pointer-events-none absolute bottom-full left-1/2 z-50 mb-2
          w-max max-w-[220px] -translate-x-1/2 rounded-lg px-3 py-2 text-xs
          leading-snug shadow-lg
          opacity-0 transition-opacity duration-150
          group-hover:opacity-100
          ${config.tooltip}
        `}
      >
        <p className="font-semibold mb-0.5">Document access</p>
        <p className="opacity-80">{config.access}</p>
        {/* Arrow */}
        <div
          className={`
            absolute left-1/2 top-full h-0 w-0 -translate-x-1/2
            border-x-4 border-t-4 border-x-transparent
            ${role === "c_level" ? "border-t-amber-900" :
              role === "hr"          ? "border-t-violet-900" :
              role === "finance"     ? "border-t-emerald-900" :
              role === "marketing"   ? "border-t-orange-900" :
              role === "engineering" ? "border-t-blue-900" :
              "border-t-slate-800"}
          `}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
