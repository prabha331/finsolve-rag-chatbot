"""
FastAPI dependency-injection helpers.

Import ``get_current_user`` and add it to any route that requires
an authenticated caller::

    @router.get("/protected")
    def protected(user: dict = Depends(get_current_user)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

# auto_error=False lets us return a cleaner 401 instead of FastAPI's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Extract and validate the Bearer token, returning the caller's identity.

    Reads the ``Authorization: Bearer <token>`` header, verifies the JWT
    signature and expiry, then returns a slim identity dict for use in
    route handlers.

    Args:
        credentials: Injected by FastAPI from the ``Authorization`` header.
                     ``None`` when the header is absent.

    Returns:
        A dict with the following keys:

        - ``email`` (str): The subject claim (``sub``) from the token.
        - ``role``  (str): The role claim embedded at login time.

    Raises:
        HTTPException(401): If the ``Authorization`` header is missing,
                            the token is malformed, or the token has expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)

    email: str | None = payload.get("sub")
    role: str | None = payload.get("role")

    if not email or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing required claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"email": email, "role": role}
