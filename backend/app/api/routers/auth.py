from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_current_user, get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.db.models.user import User
from app.domain.enums import UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

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


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
