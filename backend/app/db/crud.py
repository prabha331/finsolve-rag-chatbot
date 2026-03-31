"""
CRUD helpers for the User table.

All functions accept a SQLAlchemy ``Session`` as their first argument
so they are fully testable without touching the real database.
"""

from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import User

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return the User with the given email, or None."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_employee_id(db: Session, employee_id: str) -> Optional[User]:
    """Return the User with the given employee_id, or None."""
    return db.query(User).filter(User.employee_id == employee_id).first()


def get_all_users(db: Session) -> List[User]:
    """Return every user row ordered by id."""
    return db.query(User).order_by(User.id).all()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    role: str = "employee",
    department: Optional[str] = None,
    is_approved: bool = False,
    employee_id: Optional[str] = None,
    hr_verified: bool = False,
    verification_note: Optional[str] = None,
) -> User:
    """Hash the password and persist a new User row."""
    hashed = pwd_context.hash(password)
    user = User(
        email=email,
        employee_id=employee_id,
        full_name=full_name,
        hashed_password=hashed,
        role=role,
        department=department,
        is_approved=is_approved,
        hr_verified=hr_verified,
        verification_note=verification_note,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Password verification
# ---------------------------------------------------------------------------


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* value."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def update_user_role(
    db: Session,
    email: str,
    new_role: str,
    approved: bool = True,
) -> Optional[User]:
    """Change the role of the user identified by *email* and mark as approved."""
    user = get_user_by_email(db, email)
    if user:
        user.role = new_role
        user.is_approved = approved
        db.commit()
        db.refresh(user)
    return user


def update_user_approval(
    db: Session,
    email: str,
    approved: bool,
) -> Optional[User]:
    """Set the is_approved flag for the user identified by *email*."""
    user = get_user_by_email(db, email)
    if user:
        user.is_approved = approved
        db.commit()
        db.refresh(user)
    return user
