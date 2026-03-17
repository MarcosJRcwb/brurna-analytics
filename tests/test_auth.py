import sys
import os
import pytest
import jwt
from datetime import datetime, timedelta, timezone

# Add the src dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from auth.hasher import get_password_hash, verify_password
from auth.jwt_utils import create_access_token, create_refresh_token, decode_token, is_token_valid

def test_password_hashing():
    pwd = "super_secret_password_123"
    hashed = get_password_hash(pwd)
    
    # Must match correct password
    assert verify_password(pwd, hashed) is True
    # Must fail wrong password
    assert verify_password("wrong_password", hashed) is False

def test_access_token_creation_and_decoding():
    token = create_access_token(user_id=42, username="testadmin")
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["username"] == "testadmin"
    assert decoded["type"] == "access"
    assert "exp" in decoded

def test_refresh_token_creation_and_decoding():
    token = create_refresh_token(user_id=42)
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["type"] == "refresh"
    assert "exp" in decoded

def test_invalid_token():
    assert is_token_valid("invalid.token.string") is False

def test_expired_token(monkeypatch):
    # Create an artificially expired token
    import auth.jwt_utils as jwt_utils
    
    payload = {
        "sub": "99",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    expired_token = jwt.encode(payload, jwt_utils._SECRET, algorithm=jwt_utils._ALGORITHM)
    
    assert is_token_valid(expired_token) is False
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_token)
