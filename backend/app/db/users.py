"""
In-memory user store for demo purposes.

Passwords are bcrypt-hashed at module load time.
Replace this module with a real database layer before going to production.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pre-hash the shared demo password once so every user entry is consistent.
_HASHED_DEMO_PASSWORD = _pwd_context.hash("password123")

FAKE_DB: dict[str, dict] = {
    "alice@finsolve.com": {
        "email": "alice@finsolve.com",
        "hashed_password": _HASHED_DEMO_PASSWORD,
        "role": "finance",
        "full_name": "Alice Chen",
    },
    "bob@finsolve.com": {
        "email": "bob@finsolve.com",
        "hashed_password": _HASHED_DEMO_PASSWORD,
        "role": "engineering",
        "full_name": "Bob Kumar",
    },
    "carol@finsolve.com": {
        "email": "carol@finsolve.com",
        "hashed_password": _HASHED_DEMO_PASSWORD,
        "role": "hr",
        "full_name": "Carol Martinez",
    },
    "david@finsolve.com": {
        "email": "david@finsolve.com",
        "hashed_password": _HASHED_DEMO_PASSWORD,
        "role": "marketing",
        "full_name": "David Osei",
    },
    "eve@finsolve.com": {
        "email": "eve@finsolve.com",
        "hashed_password": _HASHED_DEMO_PASSWORD,
        "role": "employee",
        "full_name": "Eve Nakamura",
    },
    "frank@finsolve.com": {
        "email": "frank@finsolve.com",
        "hashed_password": _HASHED_DEMO_PASSWORD,
        "role": "c_level",
        "full_name": "Frank Okonkwo",
    },
}


def get_user(email: str) -> dict | None:
    """Look up a user by email address.

    Args:
        email: The user's email address (case-sensitive).

    Returns:
        The user dict if found, otherwise ``None``.
    """
    return FAKE_DB.get(email)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash.

    Args:
        plain:  The password supplied by the user at login.
        hashed: The stored bcrypt hash to verify against.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    return _pwd_context.verify(plain, hashed)
