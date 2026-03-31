"""
Authentication router.

Endpoints
---------
POST /auth/register  — self-service registration with HR verification.
POST /auth/login     — exchange credentials for a JWT access token.
GET  /auth/me        — return the identity of the currently authenticated caller.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.crud import (
    create_user,
    get_user_by_email,
    get_user_by_employee_id,
    verify_password,
)
from app.db.database import get_db
from app.services.hr_verify_service import verify_employee

router = APIRouter(prefix="/auth", tags=["Authentication"])

VALID_ROLES    = {"employee", "hr", "finance", "marketing", "engineering", "c_level"}
ALLOWED_DOMAINS = ["@finsolve.com", "@fintechco.com"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email:              str
    password:           str
    confirm_password:   str
    full_name:          str
    employee_id:        str
    claimed_department: str


class LoginRequest(BaseModel):
    email:    str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type:   str  = "bearer"
    role:         str
    email:        str
    full_name:    str
    is_approved:  bool


class UserResponse(BaseModel):
    email:       str
    role:        str
    full_name:   str
    is_approved: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    """Self-service registration with HR record verification.

    If the employee's ID + email match HR records the account is
    auto-approved with the correct role.  Otherwise the account is
    created as a pending employee awaiting admin review.
    """
    # 1. Passwords match
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    # 2. Minimum password length
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    # 3. Allowed email domain
    if not any(request.email.endswith(domain) for domain in ALLOWED_DOMAINS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only @finsolve.com or @fintechco.com email addresses are allowed.",
        )

    # 4. Email not already registered
    if get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered. Please sign in instead.",
        )

    # 5. Employee ID not already registered
    if get_user_by_employee_id(db, request.employee_id.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Employee ID is already registered.",
        )

    # 6. Verify against HR records
    hr_result = verify_employee(
        employee_id=request.employee_id.strip(),
        email=request.email.strip().lower(),
        claimed_department=request.claimed_department,
    )

    error_type = hr_result.get("error_type")

    if error_type == "csv_not_found":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error":   "hr_system_unavailable",
                "message": "HR verification system is currently unavailable. Please contact IT support.",
            },
        )

    if error_type == "employee_id_not_found":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":   "employee_id_not_found",
                "message": (
                    f"Employee ID '{request.employee_id}' was not found in our HR records. "
                    "Please check your Employee ID card and try again. "
                    "If you believe this is an error, contact HR at hr@fintechco.com"
                ),
            },
        )

    if error_type == "email_mismatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":   "email_mismatch",
                "message": (
                    f"The email address you entered does not match our HR records "
                    f"for Employee ID '{request.employee_id}'. "
                    "Please use the email address registered with HR."
                ),
            },
        )

    if error_type == "department_mismatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":              "department_mismatch",
                "message": (
                    f"Department mismatch detected. "
                    f"You selected '{hr_result['claimed_department']}' "
                    f"but our HR records show you belong to the "
                    f"'{hr_result['actual_department']}' department. "
                    "Please select the correct department and try again."
                ),
                "actual_department":  hr_result["actual_department"],
                "claimed_department": hr_result["claimed_department"],
            },
        )

    if not hr_result["verified"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":   "verification_failed",
                "message": (
                    "We could not verify your details against HR records. "
                    "Please check all fields and try again."
                ),
            },
        )

    # 7. All checks passed — create the account
    create_user(
        db=db,
        email=request.email,
        password=request.password,          # their private password — hashed in crud
        full_name=request.full_name,
        role=hr_result["suggested_role"],
        department=hr_result["actual_department"],
        is_approved=True,
        employee_id=request.employee_id.strip(),
        hr_verified=True,
        verification_note=hr_result["note"],
    )

    return {
        "message":           "Registration successful! You have been automatically verified.",
        "email":             request.email,
        "role":              hr_result["suggested_role"],
        "department":        hr_result["actual_department"],
        "is_approved":       True,
        "hr_verified":       True,
        "verification_note": hr_result["note"],
    }


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Authenticate a user and issue a JWT access token.

    Raises:
        HTTPException(401): Email not found or wrong password.
        HTTPException(403): Account not yet approved or deactivated.
    """
    user = get_user_by_email(db, request.email)

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account is pending approval. "
                "Please contact your administrator."
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated.",
        )

    token = create_access_token({"sub": user.email, "role": user.role})

    return LoginResponse(
        access_token=token,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        is_approved=user.is_approved,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Return the full profile of the currently authenticated user from the database."""
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserResponse(
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_approved=user.is_approved,
    )
