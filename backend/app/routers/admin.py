"""
Admin router — accessible only to c_level role.

Endpoints
---------
GET    /admin/users                    — list all users.
POST   /admin/users                    — create a user with any role.
PATCH  /admin/users/{email}/role       — change a user's role.
PATCH  /admin/users/{email}/approve    — approve a pending user.
DELETE /admin/users/{email}            — deactivate a user (soft-delete).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_current_user
from app.db.crud import (
    create_user,
    get_all_users,
    get_user_by_email,
    update_user_approval,
    update_user_role,
)
from app.db.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_ROLES = {"employee", "hr", "finance", "marketing", "engineering", "c_level"}


# ---------------------------------------------------------------------------
# Role guard dependency
# ---------------------------------------------------------------------------


def require_c_level(current_user: dict = Depends(get_current_user)) -> dict:
    """Raise 403 if the caller is not c_level."""
    if current_user["role"] != "c_level":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only C-Level executives can access admin functions.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class UserOut(BaseModel):
    """User representation that never exposes hashed_password."""
    id: int
    email: str
    full_name: str
    role: str
    department: Optional[str]
    is_active: bool
    is_approved: bool

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str
    department: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    role: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/users", response_model=List[UserOut])
def list_users(
    _admin: dict = Depends(require_c_level),
    db: Session = Depends(get_db),
) -> List[UserOut]:
    """Return all users (without hashed_password)."""
    return get_all_users(db)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    request: CreateUserRequest,
    _admin: dict = Depends(require_c_level),
    db: Session = Depends(get_db),
) -> UserOut:
    """Create a user with any role. Admin-created accounts are auto-approved."""
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{request.role}'. Valid roles: {sorted(VALID_ROLES)}",
        )
    if get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )
    user = create_user(
        db=db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        role=request.role,
        department=request.department,
        is_approved=True,   # admin-created → immediately approved
    )
    return user


@router.patch("/users/{email}/role", response_model=UserOut)
def set_user_role(
    email: str,
    request: UpdateRoleRequest,
    _admin: dict = Depends(require_c_level),
    db: Session = Depends(get_db),
) -> UserOut:
    """Update a user's role and mark the account as approved."""
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{request.role}'. Valid roles: {sorted(VALID_ROLES)}",
        )
    user = update_user_role(db, email, request.role, approved=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.patch("/users/{email}/approve", response_model=UserOut)
def approve_user(
    email: str,
    _admin: dict = Depends(require_c_level),
    db: Session = Depends(get_db),
) -> UserOut:
    """Approve a pending user so they can log in."""
    user = update_user_approval(db, email, approved=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.delete("/users/{email}", status_code=status.HTTP_200_OK)
def deactivate_user(
    email: str,
    _admin: dict = Depends(require_c_level),
    db: Session = Depends(get_db),
) -> dict:
    """Soft-deactivate a user (sets is_active=False, does NOT delete the row)."""
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = False
    db.commit()
    return {"message": f"User {email} has been deactivated."}
