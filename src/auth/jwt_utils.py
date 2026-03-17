"""
JWT utilities for Brurna Analytics.
Access tokens: 15 min | Refresh tokens: 7 days | Algorithm: HS256
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()

_SECRET = os.getenv("JWT_SECRET")
if not _SECRET:
    raise EnvironmentError("JWT_SECRET not set in .env")

_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 15
_REFRESH_EXPIRE_DAYS = 7


def create_access_token(user_id: int, username: str) -> str:
    """Create a short-lived access token (15 min)."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token (7 days)."""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=_REFRESH_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])


def is_token_valid(token: str) -> bool:
    """Non-raising validity check — returns True/False."""
    try:
        decode_token(token)
        return True
    except jwt.PyJWTError:
        return False
