"""
HR verification service.

Verifies a registering employee against hr_data.csv by matching both
their Employee ID and email address.  If both match, the correct RBAC
role is derived from the department recorded in HR and the account is
auto-approved.  If only the Employee ID matches but the email is wrong,
registration is blocked with an informative message.  If the Employee ID
is not found at all, the account is created as a pending-employee that
needs admin approval.
"""

import csv
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Department → RBAC role mapping
# ---------------------------------------------------------------------------

DEPT_TO_ROLE: dict[str, str] = {
    "engineering":       "engineering",
    "technology":        "engineering",
    "finance":           "finance",
    "risk":              "finance",
    "hr":                "hr",
    "human resources":   "hr",
    "marketing":         "marketing",
    "sales":             "marketing",
    "business":          "marketing",
    "product":           "marketing",
    "design":            "marketing",
    "operations":        "employee",
    "compliance":        "employee",
    "quality assurance": "employee",
    "data":              "employee",
    "general":           "employee",
    "general/other":     "employee",
    "executive":         "c_level",
    "c-suite":           "c_level",
}

# Path to hr_data.csv relative to the repo root
_REPO_DIR = Path(__file__).resolve().parent.parent.parent.parent
_HR_CSV   = _REPO_DIR / "data" / "hr" / "hr_data.csv"


def _find_column(fieldnames: list[str], candidates: list[str]) -> Optional[str]:
    """Return the first fieldname that case-insensitively matches any candidate."""
    for candidate in candidates:
        for field in fieldnames:
            if candidate.lower() == field.lower().strip():
                return field
    return None


def _load_hr_index() -> dict[str, dict]:
    """Load hr_data.csv and return a dict keyed by lower-cased employee_id.

    Returns an empty dict if the file is missing or unreadable.
    """
    if not _HR_CSV.exists():
        return {}

    index: dict[str, dict] = {}
    try:
        with open(_HR_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])

            id_col   = _find_column(fieldnames, ["employee_id", "Employee ID", "EmployeeID", "emp_id"])
            email_col = _find_column(fieldnames, ["email", "Email", "EMAIL", "email_address"])
            dept_col  = _find_column(fieldnames, ["department", "Department", "DEPARTMENT", "dept"])
            name_col  = _find_column(fieldnames, ["full_name", "Full Name", "name", "Name"])

            if not id_col or not email_col or not dept_col:
                return {}

            for row in reader:
                emp_id = (row.get(id_col) or "").strip()
                if emp_id:
                    index[emp_id.lower()] = {
                        "employee_id": emp_id,
                        "email":       (row.get(email_col) or "").strip().lower(),
                        "department":  (row.get(dept_col)  or "").strip(),
                        "full_name":   (row.get(name_col)  or "").strip() if name_col else "",
                    }
    except Exception:
        return {}

    return index


# ---------------------------------------------------------------------------
# Department alias groups for flexible matching
# ---------------------------------------------------------------------------

DEPT_ALIASES: dict[str, list[str]] = {
    "hr":                ["hr", "human resources", "human resource",
                          "people", "people ops"],
    "finance":           ["finance", "financial", "accounts", "accounting"],
    "engineering":       ["engineering", "technology", "tech",
                          "software", "it", "development"],
    "marketing":         ["marketing", "sales", "business", "growth",
                          "product", "design", "brand", "communications"],
    "operations":        ["operations", "ops", "support"],
    "compliance":        ["compliance", "legal", "regulatory"],
    "data":              ["data", "data science", "analytics",
                          "business intelligence"],
    "risk":              ["risk", "risk management"],
    "quality assurance": ["quality assurance", "qa", "quality", "testing"],
    "executive":         ["executive", "c-suite", "leadership", "management"],
}


def _departments_match(actual: str, claimed: str) -> bool:
    """Return True if *actual* and *claimed* map to the same alias group."""
    actual_lower  = actual.lower().strip()
    claimed_lower = claimed.lower().strip()
    if actual_lower == claimed_lower:
        return True
    for aliases in DEPT_ALIASES.values():
        if actual_lower in aliases and claimed_lower in aliases:
            return True
    return False


def verify_employee(
    employee_id: str,
    email: str,
    claimed_department: str,
) -> dict:
    """Verify a registering employee against HR records.

    Returns a dict with:
      - ``verified``          (bool)      — True only when all three fields match.
      - ``found``             (bool)      — True if the employee_id exists in HR.
      - ``error_type``        (str|None)  — Machine-readable failure reason, or None.
      - ``actual_department`` (str|None)  — The department on file, if found.
      - ``claimed_department``(str|None)  — Echoed back on dept mismatch.
      - ``suggested_role``    (str)       — RBAC role to assign.
      - ``note``              (str)       — Human-readable explanation.
    """
    print(f"[HR_VERIFY] Checking — id={employee_id!r} email={email!r} dept={claimed_department!r}")

    # --- CSV missing ---
    if not _HR_CSV.exists():
        print(f"[HR_VERIFY] ERROR: CSV not found at {_HR_CSV}")
        return {
            "verified":           False,
            "found":              False,
            "error_type":         "csv_not_found",
            "actual_department":  None,
            "claimed_department": None,
            "suggested_role":     "employee",
            "note":               "HR records not available.",
        }

    hr_index = _load_hr_index()

    # --- Employee ID not found ---
    record = hr_index.get(employee_id.strip().lower())
    if record is None:
        print(f"[HR_VERIFY] Employee ID not found: {employee_id!r}")
        return {
            "verified":           False,
            "found":              False,
            "error_type":         "employee_id_not_found",
            "actual_department":  None,
            "claimed_department": None,
            "suggested_role":     "employee",
            "note":               f"Employee ID '{employee_id}' not found in HR records.",
        }

    print(f"[HR_VERIFY] Found record: {record}")

    # --- Email mismatch ---
    if record["email"] != email.strip().lower():
        print(f"[HR_VERIFY] Email mismatch: {record['email']!r} vs {email!r}")
        return {
            "verified":           False,
            "found":              True,
            "error_type":         "email_mismatch",
            "actual_department":  None,
            "claimed_department": None,
            "suggested_role":     "employee",
            "note": (
                f"Email does not match HR records for Employee ID '{employee_id}'."
            ),
        }

    # --- Department mismatch ---
    actual_dept    = record["department"]
    suggested_role = DEPT_TO_ROLE.get(actual_dept.lower().strip(), "employee")

    if not _departments_match(actual_dept, claimed_department):
        print(f"[HR_VERIFY] Dept mismatch: actual={actual_dept!r} claimed={claimed_department!r}")
        return {
            "verified":           False,
            "found":              True,
            "error_type":         "department_mismatch",
            "actual_department":  actual_dept,
            "claimed_department": claimed_department,
            "suggested_role":     suggested_role,
            "note": (
                f"Department mismatch: "
                f"claimed='{claimed_department}', actual='{actual_dept}'."
            ),
        }

    # --- All checks passed ---
    print(f"[HR_VERIFY] VERIFIED — role={suggested_role!r}")
    return {
        "verified":           True,
        "found":              True,
        "error_type":         None,
        "actual_department":  actual_dept,
        "claimed_department": claimed_department,
        "suggested_role":     suggested_role,
        "note": (
            f"Auto-verified: Employee ID, email, and department matched HR records "
            f"for {actual_dept}."
        ),
    }


def get_role_for_department(department: str) -> Optional[str]:
    """Return the RBAC role for *department* (case-insensitive), or None."""
    return DEPT_TO_ROLE.get(department.strip().lower())
