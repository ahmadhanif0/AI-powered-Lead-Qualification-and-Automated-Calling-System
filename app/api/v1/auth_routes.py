import re
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel, EmailStr, field_validator

from app.auth.jwt_handler import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.retry_config import RetryConfig
from app.services.activity_logger import log_activity

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Schemas ──────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email:     EmailStr
    password:  str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


def _user_response(user: User) -> dict:
    return {
        "id":        user.id,
        "email":     user.email,
        "full_name": user.full_name,
        "role":      user.role,
        "is_active": user.is_active,
    }


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)


# ── POST /auth/signup ────────────────────────────────────────────────

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, request: Request):
    existing = await User.get_or_none(email=body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await User.create(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="user",
    )

    # Create default retry configs for new user
    await RetryConfig.create(user_id=user.id, outcome_type="call_later",  retry_delay_minutes=60, max_retry_attempts=3)
    await RetryConfig.create(user_id=user.id, outcome_type="no_response", retry_delay_minutes=30, max_retry_attempts=3)

    await log_activity(user.id, "signup", ip=_get_ip(request))

    return {
        "access_token":  create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id, user.role),
        "token_type":    "bearer",
        "user":          _user_response(user),
    }


# ── POST /auth/login ─────────────────────────────────────────────────

@router.post("/login")
async def login(body: LoginRequest, request: Request):
    user = await User.get_or_none(email=body.email)

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account is suspended")

    user.last_login = datetime.now(timezone.utc)
    await user.save()

    await log_activity(user.id, "login", ip=_get_ip(request))

    return {
        "access_token":  create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id, user.role),
        "token_type":    "bearer",
        "user":          _user_response(user),
    }


# ── POST /auth/refresh ───────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = await User.get_or_none(id=user_id)
    if not user or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type":   "bearer",
    }


# ── POST /auth/logout ────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    await log_activity(current_user.id, "logout", ip=_get_ip(request))
    return {"message": "Logged out successfully"}


# ── GET /auth/me ─────────────────────────────────────────────────────

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return _user_response(current_user)
