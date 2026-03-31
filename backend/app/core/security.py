"""
JWT creation and verification utilities.

All token operations use the algorithm and secret configured in app.core.config.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token.

    Clones *data*, appends an ``exp`` claim derived from
    ``settings.JWT_EXPIRE_MINUTES``, then signs the result with
    ``settings.JWT_SECRET_KEY`` using ``settings.JWT_ALGORITHM``.

    Args:
        data: Payload to encode.  Typically contains at minimum
              ``{"sub": "<email>", "role": "<role>"}``

    Returns:
        A compact, URL-safe JWT string.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload["exp"] = expire

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: The raw JWT string from the ``Authorization: Bearer`` header.

    Returns:
        The decoded payload as a plain ``dict``, including all original claims
        plus the ``exp`` claim added at creation time.

    Raises:
        HTTPException(401): If the token is malformed, has an invalid signature,
                            or has expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
