"""
SQLAlchemy ORM models.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    """
    Represents an authenticated FinSolve employee.

    role must be one of:
        employee | hr | finance | marketing | engineering | c_level

    is_approved:
        False  — newly registered, awaiting admin approval.
        True   — approved by admin; can log in.

    is_active:
        True  — account is live.
        False — deactivated by admin (soft-delete).
    """

    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    employee_id     = Column(String, unique=True, index=True, nullable=True)
    full_name       = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(String, default="employee", nullable=False)
    department      = Column(String, nullable=True)
    is_active         = Column(Boolean, default=True)
    is_approved       = Column(Boolean, default=False)
    hr_verified       = Column(Boolean, default=False, nullable=True)
    verification_note = Column(String, nullable=True)
    created_at        = Column(DateTime, server_default=func.now())
