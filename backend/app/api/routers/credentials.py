from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_db, get_owned_project
from app.core.security import get_cipher
from app.db.models.credential import CredentialProfile
from app.db.models.project import Project
from app.schemas.credential import CredentialCreate, CredentialOut

router = APIRouter(prefix="/projects/{project_id}/credentials", tags=["credentials"])


def _to_out(profile: CredentialProfile) -> CredentialOut:
    return CredentialOut(
        id=profile.id,
        project_id=profile.project_id,
        label=profile.label,
        has_username=bool(profile.encrypted_username),
        has_password=bool(profile.encrypted_password),
        has_api_token=bool(profile.encrypted_api_token),
        has_bearer_token=bool(profile.encrypted_bearer_token),
        has_cookies=bool(profile.encrypted_cookies),
        has_headers=bool(profile.encrypted_headers),
    )


@router.post("", response_model=CredentialOut, status_code=status.HTTP_201_CREATED)
async def create_credential(
    payload: CredentialCreate,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> CredentialOut:
    cipher = get_cipher()
    import json

    profile = CredentialProfile(
        project_id=project.id,
        label=payload.label,
        encrypted_username=cipher.encrypt(payload.username) if payload.username else None,
        encrypted_password=cipher.encrypt(payload.password) if payload.password else None,
        encrypted_api_token=cipher.encrypt(payload.api_token) if payload.api_token else None,
        encrypted_bearer_token=cipher.encrypt(payload.bearer_token) if payload.bearer_token else None,
        encrypted_cookies=cipher.encrypt(json.dumps(payload.cookies)) if payload.cookies else None,
        encrypted_headers=cipher.encrypt(json.dumps(payload.headers)) if payload.headers else None,
        encrypted_env_vars=cipher.encrypt(json.dumps(payload.env_vars)) if payload.env_vars else None,
    )
    session.add(profile)
    await session.commit()
    return _to_out(profile)


@router.get("", response_model=list[CredentialOut])
async def list_credentials(
    project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)
) -> list[CredentialOut]:
    profiles = (
        await session.execute(select(CredentialProfile).where(CredentialProfile.project_id == project.id))
    ).scalars().all()
    return [_to_out(p) for p in profiles]


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> None:
    profile = await session.get(CredentialProfile, credential_id)
    if profile is None or profile.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credential not found")
    await session.delete(profile)
    await session.commit()
