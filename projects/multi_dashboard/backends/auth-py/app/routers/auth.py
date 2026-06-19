from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from shared.auth import decode_jwt, encode_jwt
from shared.errors import AuthError, NotFoundError
from shared.errors import ValidationError as AppValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..crud.users import create_user, get_user_by_email, get_user_by_id, update_user
from ..deps import get_db
from ..schemas.token import RefreshRequest, Token
from ..schemas.user import UserCreate, UserOut
from ..security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def _issue_tokens(user_id: str, email: str, role: str, settings: Any) -> Token:
    access = encode_jwt(
        {"sub": user_id, "email": email, "role": role},
        settings.auth_secret_key,
        settings.auth_algorithm,
        expires_in_seconds=settings.access_token_expire_minutes * 60,
    )
    refresh = encode_jwt(
        {"sub": user_id, "email": email, "role": role},
        settings.auth_secret_key,
        settings.auth_algorithm,
        expires_in_seconds=settings.refresh_token_expire_days * 86400,
        token_type="refresh",
    )
    return Token(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/token", response_model=Token)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await get_user_by_email(db, form_data.username)
    if not user or not user.password_hash:
        raise AuthError("Incorrect username or password")
    if not verify_password(form_data.password, user.password_hash):
        raise AuthError("Incorrect username or password")
    if not user.is_active:
        raise AuthError("Account is inactive")
    return _issue_tokens(str(user.id), user.email, user.role, get_settings())


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    return await token(form_data=form_data, db=db)


@router.post("/refresh", response_model=Token)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    settings = get_settings()
    try:
        claims = decode_jwt(
            body.refresh_token,
            settings.auth_secret_key,
            settings.auth_algorithm,
            expected_type=None,
        )
    except Exception as exc:
        raise AuthError("Invalid or expired refresh token") from exc

    if claims.type != "refresh":
        raise AuthError("Not a refresh token")

    user = await get_user_by_id(db, uuid.UUID(claims.sub))
    if not user or not user.is_active:
        raise AuthError("User not found or inactive")

    return _issue_tokens(str(user.id), user.email, user.role, settings)


@router.get("/me", response_model=UserOut)
async def me(
    token_str: str | None = Depends(_oauth2),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if not token_str:
        raise AuthError("Missing bearer token")
    settings = get_settings()
    try:
        claims = decode_jwt(token_str, settings.auth_secret_key, settings.auth_algorithm)
    except Exception as exc:
        raise AuthError("Invalid token") from exc

    user = await get_user_by_id(db, uuid.UUID(claims.sub))
    if not user:
        raise NotFoundError("User not found")
    return UserOut.model_validate(user)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    existing = await get_user_by_email(db, body.email)
    if existing:
        if existing.password_hash:
            raise AppValidationError("Email already registered")
        updated = await update_user(
            db, existing, {"password_hash": hash_password(body.password)}
        )
        await db.commit()
        return UserOut.model_validate(updated)

    user = await create_user(
        db,
        email=body.email,
        password=body.password,
        name=body.name,
        role=body.role,
    )
    await db.commit()
    return UserOut.model_validate(user)
