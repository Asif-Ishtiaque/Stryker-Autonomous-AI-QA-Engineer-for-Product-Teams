from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr

from app.domain.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role: UserRole

    model_config = {"from_attributes": True}
