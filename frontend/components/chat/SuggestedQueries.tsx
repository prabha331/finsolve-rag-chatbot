"use client";

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

interface RoleData {
  displayName: string;
  icon: string;
  queries: string[];
}

const ROLE_DATA: Record<string, RoleData> = {
  employee: {
    displayName: "Employee",
    icon: "👤",
    queries: [
      "How many sick leave days do I get per year?",
      "What is the dress code policy?",
      "How do I apply for reimbursement?",
      "What are the work from home rules?",
    ],
  },
  hr: {
    displayName: "HR",
    icon: "🏢",
    queries: [
      "Which employees have the highest performance ratings?",
      "What is the average salary by department?",
      "How many employees joined in 2024?",
      "What is our current attrition rate?",
    ],
  },
  finance: {
    displayName: "Finance",
    icon: "📊",
    queries: [
      "What was the net income in Q4 2024?",
      "How did gross margin trend across all quarters?",
      "What were the top expense categories in 2024?",
      "Compare Q1 vs Q4 revenue growth",
    ],
  },
  marketing: {
    displayName: "Marketing",
    icon: "📣",
    queries: [
      "What was the total marketing spend in 2024?",
      "Which campaign had the highest ROI?",
      "What were the Q3 customer acquisition targets?",
      "How did our conversion rate change from Q1 to Q4?",
    ],
  },
  engineering: {
    displayName: "Engineering",
    icon: "⚙️",
    queries: [
      "What is our microservices architecture?",
      "What compliance standards do we follow?",
      "What does our CI/CD pipeline look like?",
      "What is the future tech roadmap?",
    ],
  },
  c_level: {
    displayName: "C-Level Executive",
    icon: "⭐",
    queries: [
      "Give me an executive summary of Q4 2024 financial performance",
      "How does our engineering compliance compare to requirements?",
      "What is the overall employee performance distribution?",
      "Compare marketing ROI across all four quarters",
    ],
  },
};

const FALLBACK: RoleData = {
  displayName: "User",
  icon: "💬",
  queries: [
    "What documents do I have access to?",
    "Tell me about FinSolve Technologies",
    "What is the employee handbook?",
    "How can I get help?",
  ],
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SuggestedQueriesProps {
  role: string;
  onSelect: (query: string) => void;
}

export default function SuggestedQueries({ role, onSelect }: SuggestedQueriesProps) {
  const data = ROLE_DATA[role] ?? FALLBACK;

  return (
    <div className="flex flex-col items-center gap-8 px-4 py-10 text-center">

      {/* Bot avatar + greeting */}
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 shadow-md shadow-blue-200">
          <span className="text-lg font-bold tracking-tight text-white">FS</span>
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-800">
            How can I help you today?
          </h2>
          <p className="text-sm text-slate-500">
            I have access to the documents permitted for your role.
          </p>
        </div>
      </div>

      {/* Role label */}
      <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-1.5">
        <span aria-hidden="true">{data.icon}</span>
        <span className="text-xs font-medium text-slate-600">
          Suggested questions for{" "}
          <span className="font-semibold text-slate-800">{data.displayName}</span>
        </span>
      </div>

      {/* 2×2 query cards */}
      <div className="grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2">
        {data.queries.map((query) => (
          <button
            key={query}
            type="button"
            onClick={() => onSelect(query)}
            className="
              group rounded-xl border border-slate-200 bg-white px-4 py-3.5
              text-left text-sm text-slate-700 shadow-sm
              transition-all duration-150
              hover:border-blue-300 hover:bg-blue-50 hover:shadow-md hover:text-blue-800
              active:scale-[0.98]
            "
          >
            <div className="flex items-start justify-between gap-2">
              <span className="leading-snug">{query}</span>
              {/* Arrow indicator */}
              <svg
                className="mt-0.5 h-4 w-4 shrink-0 text-slate-300 transition-colors group-hover:text-blue-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </div>
          </button>
        ))}
      </div>

      {/* Disclaimer */}
      <p className="max-w-sm text-[11px] text-slate-400">
        Answers are generated from your accessible internal documents only.
        Results are limited to your role permissions.
      </p>
    </div>
  );
}
