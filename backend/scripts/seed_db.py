"""
Seed script — populates the SQLite database with demo accounts only.

Real fintechco.com employees must register themselves via /register
and set their own private password.  This script ONLY seeds the 6
named demo/presentation accounts plus cleans up any incorrectly
pre-seeded fintechco accounts from earlier versions of this script.

Usage (run from the backend/ directory)::

    python scripts/seed_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.crud import create_user, get_user_by_email          # noqa: E402
from app.db.database import DATABASE_URL, SessionLocal, create_all_tables  # noqa: E402
from app.db.models import User                                  # noqa: E402

# ---------------------------------------------------------------------------
# Demo accounts — for presentation / quick-login only.
# Real employees must NOT be pre-seeded here.
# ---------------------------------------------------------------------------

DEMO_USERS = [
    {"email": "alice@finsolve.com",  "password": "password123", "full_name": "Alice Chen",   "role": "finance",     "department": "Finance",     "is_approved": True},
    {"email": "bob@finsolve.com",    "password": "password123", "full_name": "Bob Kumar",    "role": "engineering", "department": "Engineering", "is_approved": True},
    {"email": "carol@finsolve.com",  "password": "password123", "full_name": "Carol Davis",  "role": "hr",          "department": "HR",          "is_approved": True},
    {"email": "david@finsolve.com",  "password": "password123", "full_name": "David Park",   "role": "marketing",   "department": "Marketing",   "is_approved": True},
    {"email": "eve@finsolve.com",    "password": "password123", "full_name": "Eve Johnson",  "role": "employee",    "department": "General",     "is_approved": True},
    {"email": "frank@finsolve.com",  "password": "password123", "full_name": "Frank Wilson", "role": "c_level",     "department": "Executive",   "is_approved": True},
]


# ---------------------------------------------------------------------------
# Step 0a: Remove accounts with known typo emails from earlier seed runs
# ---------------------------------------------------------------------------

TYPO_EMAILS = [
    "alice@ffinsolve.com",  "alice@finnsolve.com",
    "bob@ffinsolve.com",    "bob@finnsolve.com",    "bob@finsoolve.com",
    "carol@ffinsolve.com",  "carol@finnsolve.com",
    "david@ffinsolve.com",  "david@finnsolve.com",
    "eve@ffinsolve.com",    "eve@finnsolve.com",    "eve@finsoolve.com",
    "frank@ffinsolve.com",  "frank@finnsolve.com",
]


def cleanup_typo_emails(db) -> None:
    """Delete any accounts that were seeded with misspelled email addresses."""
    deleted = 0
    for email in TYPO_EMAILS:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            deleted += 1
    db.commit()
    if deleted:
        print(f"🗑️  Removed {deleted} typo-email account(s)")
    else:
        print("✅ No typo-email accounts found")


# ---------------------------------------------------------------------------
# Step 0b: Remove pre-seeded fintechco accounts from previous script versions
# ---------------------------------------------------------------------------

def cleanup_preseeded_employees(db) -> None:
    """Delete fintechco.com accounts that were incorrectly pre-seeded by older
    versions of this script so those employees can self-register with their
    own private passwords.

    Accounts self-registered by real employees are NOT touched because their
    verification_note will not match any of the old seed values below.
    """
    old_seed_notes = [
        "Pre-seeded from HR records",
        "Updated from HR records",
        "Seeded from HR records",
        "Bulk approved by seed script",
        "Bulk approved - fintechco employee",
        "Pre-seeded from HR data",
    ]

    deleted = (
        db.query(User)
        .filter(
            User.email.like("%@fintechco.com"),
            User.verification_note.in_(old_seed_notes),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    print(f"🗑️  Removed {deleted} pre-seeded fintechco employee account(s)")
    if deleted:
        print("   Those employees must now self-register with their own passwords.")


# ---------------------------------------------------------------------------
# Step 1: Approve any remaining pending demo users
# ---------------------------------------------------------------------------

def approve_all_existing_users(db) -> None:
    """Set is_approved=True for every user that is currently stuck as pending.

    This fixes any accounts that were created before the approval workflow
    was in place.
    """
    pending = db.query(User).filter(User.is_approved == False).all()  # noqa: E712
    for user in pending:
        user.is_approved = True
        user.verification_note = "Bulk approved by seed script"
    db.commit()
    print(f"✅ Approved {len(pending)} previously pending user(s)")


# ---------------------------------------------------------------------------
# Step 2: Seed the 6 named demo accounts
# ---------------------------------------------------------------------------

def seed_demo_users(db) -> None:
    """Create named demo accounts if they do not already exist."""
    created = 0
    for u in DEMO_USERS:
        existing = get_user_by_email(db, u["email"])
        if not existing:
            create_user(
                db=db,
                email=u["email"],
                password=u["password"],
                full_name=u["full_name"],
                role=u["role"],
                department=u["department"],
                is_approved=u["is_approved"],
            )
            print(f"  ✅ Created demo account: {u['email']} ({u['role']})")
            created += 1
        else:
            # Always keep demo accounts approved.
            if not existing.is_approved:
                existing.is_approved = True
                db.commit()
            print(f"  ⏭️  Already exists: {u['email']}")

    skipped = len(DEMO_USERS) - created
    print(f"Demo users: {created} created, {skipped} already present")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def seed() -> None:
    """Run the full seed pipeline (idempotent)."""
    create_all_tables()
    db = SessionLocal()
    try:
        print("\n--- Step 0a: Remove typo-email accounts ---")
        cleanup_typo_emails(db)

        print("\n--- Step 0b: Remove pre-seeded fintechco accounts ---")
        cleanup_preseeded_employees(db)

        print("\n--- Step 1: Approve any pending users ---")
        approve_all_existing_users(db)

        print("\n--- Step 2: Seed demo accounts ---")
        seed_demo_users(db)

        print(f"\n✅ Seed complete.")
        print(f"📁 Database: {DATABASE_URL}")
        print("ℹ️  Real fintechco.com employees must register at /register")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
