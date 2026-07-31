"""Auth (JWT + password hashing) and credential-at-rest encryption.

Two distinct trust boundaries are handled here:
  1. Platform auth — who is allowed to use Stryker (JWT, RBAC roles).
  2. AUT credentials — usernames/passwords/tokens for the application UNDER
     TEST, which Stryker stores on the user's behalf and must never persist
     in plaintext. These are encrypted with Fernet (AES-128-CBC + HMAC)
     using a key that is itself never stored in the database.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_expire_minutes),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": now + dt.timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


class CredentialCipher:
    """Encrypts/decrypts secret material stored on CredentialProfile rows."""

    def __init__(self, key: str | None = None) -> None:
        settings = get_settings()
        self._fernet = Fernet((key or settings.credential_encryption_key).encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()


def get_cipher() -> CredentialCipher:
    return CredentialCipher()
