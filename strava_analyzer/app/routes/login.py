import logging
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from strava_analyzer.app.services.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["authentication"])


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class UserInfo(BaseModel):
    username: str


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username and password to get an access token.

    Use the returned token in the Authorization header:
    `Authorization: Bearer <token>`
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    logger.info(f"User {user} logged in successfully")

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """
    Get the current authenticated user's info.
    Useful for checking if the token is still valid.
    """
    return UserInfo(username=current_user)


@router.post("/hash-password")
async def hash_password_util(password: str):
    """
    Utility endpoint to generate a password hash.
    Only available when no admin credentials are configured (for initial setup).
    Use the generated hash in ADMIN_PASSWORD_HASH environment variable.

    NOTE: This endpoint should be disabled in production after initial setup.
    """
    import os
    if os.getenv("ADMIN_USERNAME") or os.getenv("ADMIN_USERS"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password hashing disabled when admin credentials are configured"
        )

    return {
        "password": password,
        "hash": get_password_hash(password),
        "note": "Add this hash to ADMIN_PASSWORD_HASH environment variable"
    }
