"""
RBAC enforcement layer with keyword-based topic detection.

``ROLE_PERMISSIONS`` maps each role to the ChromaDB departments it may query.
``detect_restricted_topic`` intercepts queries before they ever reach the
vector store and returns a formatted access-denied message when the query
touches a department the caller cannot see.
"""

import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Role → allowed departments
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "employee":    ["employee_handbook"],
    "hr":          ["employee_handbook", "hr"],
    "finance":     ["employee_handbook", "finance"],
    "marketing":   ["employee_handbook", "marketing"],
    "engineering": ["employee_handbook", "engineering"],
    "c_level":     ["employee_handbook", "hr", "finance", "marketing", "engineering"],
}

# ---------------------------------------------------------------------------
# Human-readable labels
# ---------------------------------------------------------------------------

ROLE_DISPLAY_NAMES: Dict[str, str] = {
    "employee":    "General Employee",
    "hr":          "HR Department",
    "finance":     "Finance Department",
    "marketing":   "Marketing Department",
    "engineering": "Engineering Department",
    "c_level":     "C-Level Executive",
}

ROLE_ACCESS_DESCRIPTION: Dict[str, str] = {
    "employee":    "Employee Handbook only",
    "hr":          "Employee Handbook + HR Data",
    "finance":     "Employee Handbook + Finance Reports",
    "marketing":   "Employee Handbook + Marketing Reports",
    "engineering": "Employee Handbook + Engineering Docs",
    "c_level":     "All Documents (Full Access)",
}

# ---------------------------------------------------------------------------
# Intent-based restricted topic detection (regex patterns)
# ---------------------------------------------------------------------------

INTENT_PATTERNS: Dict[str, Dict] = {
    "hr_data": {
        "patterns": [
            # Headcount / employee numbers
            r"how many (employees|people|staff|workers)",
            r"total (headcount|employees|staff|workforce)",
            r"number of (employees|people|staff)",
            r"employee count",
            r"workforce size",
            r"how many.*resigned",
            r"how many.*joined",
            r"how many.*left",
            r"how many.*hired",
            r"how many.*terminated",
            r"employees? (resigned|quit|left|joined|hired|fired|terminated)",
            r"attrition rate",
            r"turnover rate",
            r"resignation (rate|count|number)",
            r"who (resigned|quit|left|joined)",
            r"(average|mean) salary",
            r"salary (data|by department|distribution|range)",
            r"compensation (data|analysis|review)",
            r"pay (scale|grade|band)",
            r"performance (rating|score) of",
            r"top performers",
            r"(employee|staff) performance",
            r"leave (balance|utilization) of",
            # Salary / pay — additional patterns
            r"(average|mean|median) (employee |staff )?salary",
            r"salary (range|data|information|details)",
            r"(employee|staff|worker) (salary|pay|wage|compensation)",
            r"how much (do|does|are) .*(earn|paid|make)",
            r"(pay|wage|compensation) (scale|grade|band|range)",
            r"salary by (department|role|position|level)",
            r"what (is|are) .*(salaries|wages|pay)",
            r"(highest|lowest|average) (paid|salary|wage|earner)",
            r"income of employees",
            r"(annual|monthly) (salary|pay|wage|compensation)",
        ],
        "allowed_roles": ["hr", "c_level"],
        "message": "HR Data",
    },
    "finance_data": {
        "patterns": [
            r"(total|annual|quarterly) (revenue|income|profit|earnings)",
            r"net income",
            r"gross margin",
            r"operating income",
            r"cash flow",
            r"total expenses",
            r"expense (breakdown|report|analysis)",
            r"vendor (cost|expense)",
            r"financial (report|summary|performance|ratio)",
            r"(q1|q2|q3|q4) (revenue|income|profit|earnings)",
            r"year.?over.?year",
            r"yoy (growth|change)",
            r"balance sheet",
            r"accounts (payable|receivable)",
            r"days sales outstanding",
            r"return on investment",
            r"ebitda",
            r"profit margin",
            r"budget (allocation|breakdown|spent)",
            r"how much (did we earn|did we make|revenue|profit)",
            r"what (was|were|is) the (revenue|income|profit|expenses|earnings)",
            # Revenue growth / comparison — additional patterns
            r"(revenue|income|profit|earnings) (growth|change|trend)",
            r"compare .*(revenue|income|profit|earnings)",
            r"(q1|q2|q3|q4) .*(revenue|income|profit|earnings)",
            r"revenue .*(q1|q2|q3|q4)",
            r"(quarter|quarterly) (revenue|income|performance)",
            r"(growth|increase|decrease) .*(revenue|income)",
            r"how (much|did) .*(revenue|income|profit|earn)",
            r"financial (growth|performance|results|data)",
            r"(annual|yearly) (revenue|income|profit|earnings)",
            r"(total|overall) (revenue|income|profit|expenses)",
        ],
        "allowed_roles": ["finance", "c_level"],
        "message": "Finance Data",
    },
    "engineering_data": {
        "patterns": [
            r"(micro)?services? architecture",
            r"ci/?cd (pipeline|process|workflow)",
            r"deployment (process|pipeline|strategy)",
            r"system architecture",
            r"(gdpr|pci.?dss|dpdp) compliance",
            r"compliance standards",
            r"what (compliance|standards) do we follow",
            r"security (model|architecture|compliance)",
            r"tech(nology)? (stack|roadmap)",
            r"(kubernetes|docker|k8s) (setup|config|cluster)",
            r"cloud infrastructure",
            r"devops (practices|process|workflow)",
            r"monitoring (setup|tools|system)",
            r"(api|database) (design|schema|architecture)",
            r"how do we deploy",
            r"release (process|pipeline|management)",
            r"infrastructure (setup|design|overview)",
        ],
        "allowed_roles": ["engineering", "c_level"],
        "message": "Engineering Documentation",
    },
    "marketing_data": {
        "patterns": [
            r"marketing (spend|budget|campaign|report|roi|metrics)",
            r"(total|annual|quarterly) marketing",
            r"customer acquisition (cost|target|data)",
            r"(ad|advertising) spend",
            r"return on ad spend",
            r"roas",
            r"influencer (campaign|partnership|marketing)",
            r"digital (marketing|advertising) (campaign|metrics|performance)",
            r"brand awareness (campaign|statistics|data)",
            r"marketing (q1|q2|q3|q4)",
            r"campaign (performance|roi|results|analysis)",
            r"conversion rate (target|data|analysis)",
            r"click.?through rate",
            r"cost per acquisition",
            r"customer lifetime value",
            r"market expansion (strategy|plan|data)",
            # Conversion / acquisition — additional patterns
            r"conversion rate",
            r"(q1|q2|q3|q4) .*(conversion|acquisition|campaign)",
            r"conversion .*(change|trend|improvement|q1|q2|q3|q4)",
            r"(customer|lead) (conversion|acquisition) rate",
            r"how .*(conversion rate|cac|roas|ctr)",
            r"(click.?through|click through) rate",
            r"(marketing|campaign|ad) (performance|results|metrics)",
            r"(customer|user) acquisition (cost|data|metric)",
        ],
        "allowed_roles": ["marketing", "c_level"],
        "message": "Marketing Reports",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_allowed_sources(role: str) -> List[str]:
    """Return the department collections accessible to *role*.

    Raises:
        ValueError: If *role* is not present in ``ROLE_PERMISSIONS``.
    """
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: '{role}'. Valid roles: {list(ROLE_PERMISSIONS)}")
    return ROLE_PERMISSIONS[role]


def get_role_description(role: str) -> str:
    """Return a human-readable label describing role and access level.

    Example: "Finance Department — Access: Employee Handbook + Finance Reports"
    """
    display  = ROLE_DISPLAY_NAMES.get(role, role)
    access   = ROLE_ACCESS_DESCRIPTION.get(role, "Employee Handbook only")
    return f"{display} — Access: {access}"


def get_accessible_topics(role: str) -> str:
    """Return a formatted bullet list of topics the role can query."""
    topics: Dict[str, str] = {
        "employee": (
            "• Company policies and procedures\n"
            "  - Leave policies (sick leave, casual leave, etc.)\n"
            "  - Work hours and attendance rules\n"
            "  - Dress code and workplace behaviour\n"
            "  - Compensation structure and payroll info\n"
            "  - Benefits and reimbursement policies\n"
            "  - Training and development programs\n"
            "  - Exit procedures and FAQs"
        ),
        "hr": (
            "• All Employee Handbook topics\n"
            "  - Employee records and demographics\n"
            "  - Salary and compensation data by department\n"
            "  - Attrition and turnover rates\n"
            "  - Leave utilisation and balances\n"
            "  - Performance ratings and reviews\n"
            "  - Headcount and workforce analytics\n"
            "  - Recruitment and hiring data"
        ),
        "finance": (
            "• All Employee Handbook topics\n"
            "  - Quarterly financial reports (Q1–Q4 2024)\n"
            "  - Annual revenue and income figures\n"
            "  - Gross margin and operating income\n"
            "  - Expense breakdowns and vendor costs\n"
            "  - Cash flow analysis\n"
            "  - Financial ratios and KPIs (DSO, ROI, etc.)\n"
            "  - Risk mitigation strategies\n"
            "  - Year-over-year financial performance"
        ),
        "marketing": (
            "• All Employee Handbook topics\n"
            "  - Marketing campaign reports (Q1–Q4 2024)\n"
            "  - Total marketing spend and budget\n"
            "  - Customer acquisition cost (CAC)\n"
            "  - Campaign ROI and ROAS\n"
            "  - Digital marketing metrics\n"
            "  - Brand awareness statistics\n"
            "  - Market expansion strategies\n"
            "  - Conversion rates and CTR"
        ),
        "engineering": (
            "• All Employee Handbook topics\n"
            "  - System architecture documentation\n"
            "  - CI/CD pipeline and DevOps practices\n"
            "  - Security models and compliance standards\n"
            "  - Tech stack and infrastructure\n"
            "  - Monitoring and logging setup\n"
            "  - Future technology roadmap\n"
            "  - Development standards and guidelines"
        ),
        "c_level": (
            "• All documents across ALL departments\n"
            "  - Financial reports and summaries\n"
            "  - HR data and workforce analytics\n"
            "  - Marketing performance reports\n"
            "  - Engineering architecture docs\n"
            "  - Employee Handbook and policies"
        ),
    }
    return topics.get(role, "• Employee Handbook topics only")


def detect_restricted_topic(query: str, role: str) -> Dict:
    """
    Uses regex pattern matching to detect query intent.
    Much more accurate than simple keyword matching.
    """
    # Normalise — critical: role from JWT may arrive with unexpected casing
    role        = role.strip().lower()
    query_lower = query.lower().strip()

    print(f"[RBAC] query='{query_lower}' | role='{role}'")

    for topic, config in INTENT_PATTERNS.items():
        allowed = config["allowed_roles"]

        print(f"[RBAC] topic={topic} | allowed_roles={allowed}")

        # CRITICAL: skip entirely if this role is authorised for the topic
        if role in allowed:
            print(f"[RBAC] role '{role}' IS in allowed_roles — skipping {topic}")
            continue

        # Role is NOT authorised — check whether the query matches any pattern
        for pattern in config["patterns"]:
            if re.search(pattern, query_lower):
                print(f"[RBAC] BLOCKED — pattern '{pattern}' matched topic '{topic}' for role '{role}'")

                role_display = ROLE_DISPLAY_NAMES.get(role, role)
                access_desc  = ROLE_ACCESS_DESCRIPTION.get(role, "Employee Handbook only")
                accessible   = get_accessible_topics(role)
                dept_name    = config["message"]

                message = (
                    f"🔒 **Access Denied**\n\n"
                    f"You are logged in as **{role_display}**.\n\n"
                    f"Your account has access to: **{access_desc}**\n\n"
                    f"The information you requested relates to **{dept_name}**, "
                    f"which requires special authorisation.\n\n"
                    f"**What you can ask me:**\n"
                    f"{accessible}\n\n"
                    f"If you need access to this data, please contact your administrator."
                )

                return {
                    "is_restricted":         True,
                    "restricted_topic":      topic,
                    "access_denied_message": message,
                }

    print(f"[RBAC] ALLOWED — no restriction matched for role '{role}'")
    return {
        "is_restricted":         False,
        "restricted_topic":      None,
        "access_denied_message": None,
    }


def is_role_valid(role: str) -> bool:
    """Return True if *role* is a recognised role."""
    return role in ROLE_PERMISSIONS
