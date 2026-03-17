"""Password hashing via bcrypt."""

import bcrypt

def get_password_hash(plain: str) -> str:
    """Hash a plaintext password."""
    # bcrypt requires bytes
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored hash."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
