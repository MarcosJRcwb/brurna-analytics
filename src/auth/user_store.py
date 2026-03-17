"""
User CRUD and refresh-token persistence against the project's PostgreSQL.
All DB operations re-use the existing SQLAlchemy engine from db_writer.
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from database.db_writer import engine
from auth.hasher import get_password_hash, verify_password

_REFRESH_DAYS = 7


def create_user(username: str, password: str) -> int:
    """
    Insert a new user. Returns the new user id.
    Raises ValueError if username is already taken.
    """
    hashed = get_password_hash(password)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO users (username, password_hash) "
                "VALUES (:u, :h) RETURNING id"
            ),
            {"u": username, "h": hashed},
        )
        return result.scalar_one()


def authenticate_user(username: str, password: str) -> Optional[int]:
    """
    Return user_id if credentials are valid and account is active, else None.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, password_hash FROM users "
                "WHERE username = :u AND is_active = TRUE"
            ),
            {"u": username},
        ).fetchone()
    if row and verify_password(password, row.password_hash):
        return row.id
    return None


def save_refresh_token(user_id: int, token: str) -> None:
    """Persist a refresh token for the given user."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=_REFRESH_DAYS)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO refresh_tokens (user_id, token, expires_at) "
                "VALUES (:uid, :tok, :exp)"
            ),
            {"uid": user_id, "tok": token, "exp": expires_at},
        )


def validate_refresh_token(token: str) -> Optional[int]:
    """Return user_id if token exists and is not expired, else None."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT user_id, expires_at FROM refresh_tokens "
                "WHERE token = :tok"
            ),
            {"tok": token},
        ).fetchone()
    if row and row.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        return row.user_id
    return None


def revoke_refresh_token(token: str) -> None:
    """Delete a refresh token (logout)."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM refresh_tokens WHERE token = :tok"),
            {"tok": token},
        )
