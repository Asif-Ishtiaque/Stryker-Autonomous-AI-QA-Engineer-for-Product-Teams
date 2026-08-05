from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_current_user, get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.models.user import User
from app.domain.enums import UserRole
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, payload: RegisterRequest, session: AsyncSession = Depends(get_db)) -> User:
    existing = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    is_first_user = (await session.execute(select(User.id).limit(1))).first() is None
    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
        role=UserRole.OWNER if is_first_user else UserRole.MEMBER,
    )
    session.add(user)
    await session.commit()
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.role)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, payload: RefreshRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchanges a refresh token for a new access token, without requiring the
    user to log in again. Refresh tokens were being issued at login and stored
    by the frontend since the very first version of this app, but nothing
    ever accepted one back — every session just died outright when the
    60-minute access token expired, regardless of the refresh token sitting
    unused in localStorage.

    Rotates the refresh token on every use (returns a new one alongside the
    new access token) rather than reusing the same one indefinitely — this is
    a plain JWT scheme with no server-side token store, so an old refresh
    token can't be explicitly revoked, but rotation at least limits how long
    a leaked refresh token stays valid before the legitimate client's next
    refresh silently supersedes it.
    """
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(decoded["sub"])
    except Exception as exc:  # noqa: BLE001 — any decode failure means "not a valid refresh token"
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token") from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.role)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
