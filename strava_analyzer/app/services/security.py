import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)

# Configuration from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-a-random-32-char-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_admin_credentials() -> dict[str, str]:
    """
    Get admin credentials from environment.
    Supports multiple users via comma-separated values.
    Format: ADMIN_USERS=user1:hash1,user2:hash2
    Or simple: ADMIN_USERNAME and ADMIN_PASSWORD_HASH
    """
    users = {}

    # Simple single-user setup
    username = os.getenv("ADMIN_USERNAME")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH")
    if username and password_hash:
        users[username] = password_hash

    # Multi-user setup: ADMIN_USERS=user1:hash1,user2:hash2
    admin_users = os.getenv("ADMIN_USERS", "")
    for entry in admin_users.split(","):
        if ":" in entry:
            user, hash_val = entry.strip().split(":", 1)
            users[user] = hash_val

    return users


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """Generate password hash. Use this to generate hashes for ADMIN_PASSWORD_HASH."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def authenticate_user(username: str, password: str) -> Optional[str]:
    """
    Authenticate a user and return the username if valid.
    """
    users = get_admin_credentials()

    if username not in users:
        return None

    if not verify_password(password, users[username]):
        return None

    return username


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[str]:
    """Decode and validate a JWT token, returning the username."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency to get the current authenticated user.
    Raises 401 if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    username = decode_token(token)
    if username is None:
        raise credentials_exception

    return username


# Optional dependency - returns None if not authenticated instead of raising
async def get_optional_user(token: str = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Dependency that returns the user if authenticated, None otherwise.
    Does not raise an exception for unauthenticated requests.
    """
    try:
        return await get_current_user(token)
    except HTTPException:
        return None
