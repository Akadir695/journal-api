from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.crud.refresh_token import RefreshTokenCrud
from app.crud.user import UserCrud
from app.db.session import get_db
from app.schemas.user import RefreshRequest, Token, UserCreate, UserRead
from app.crud.one_time_token import consume_token
from app.schemas.user import RefreshRequest, Token, UserCreate, UserRead, VerifyEmailRequest
from app.db.models.user import User
from app.core.security import hash_password
from arq import ArqRedis

from app.api.deps import get_arq
from app.crud.one_time_token import consume_token, create_token
from app.schemas.user import (
    ForgotPasswordRequest,
    RefreshRequest,
    Token,
    UserCreate,
    UserRead,
    VerifyEmailRequest,
    ResetPasswordRequest
)
settings = get_settings()

router = APIRouter()


def get_user_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> UserCrud:
    return UserCrud(db)


def get_refresh_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> RefreshTokenCrud:
    return RefreshTokenCrud(db)


@router.post("/auth/register", status_code=201)
async def register(
    data: UserCreate,
    crud: Annotated[UserCrud, Depends(get_user_crud)],
    db: Annotated[AsyncSession, Depends(get_db)],
    arq: Annotated[ArqRedis, Depends(get_arq)],
) -> UserRead:
    if await crud.get_by_email(data.email) is not None:
        raise ConflictError("Email already registered")
    if await crud.get_by_username(data.username) is not None:
        raise ConflictError("Username already taken")

    created = await crud.create(data)
    token = await create_token(db, created.id, "verify_email", ttl_minutes=1440)
    await arq.enqueue_job("send_verification_email", created.email, token)
    return created


@router.post("/auth/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    crud: Annotated[UserCrud, Depends(get_user_crud)],
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> Token:
    user = await crud.get_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")

    access = create_access_token(str(user.id), settings.access_token_expire_minutes)
    refresh = create_refresh_token()
    await tokens.create(user.id, refresh)

    return Token(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh")
async def refresh(
    data: RefreshRequest,
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> Token:
    row = await tokens.get_by_token(data.refresh_token)

    if row is None:
        raise UnauthorizedError("Invalid refresh token")

    if row.revoked_at is not None:
        await tokens.revoke_all_for_user(row.user_id)
        raise UnauthorizedError("Invalid refresh token")

    if row.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Invalid refresh token")

    await tokens.revoke(row)

    access = create_access_token(str(row.user_id), settings.access_token_expire_minutes)
    new_refresh = create_refresh_token()
    await tokens.create(row.user_id, new_refresh)

    return Token(access_token=access, refresh_token=new_refresh)


@router.post("/auth/logout", status_code=204)
async def logout(
    data: RefreshRequest,
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> None:
    row = await tokens.get_by_token(data.refresh_token)
    if row is not None and row.revoked_at is None:
        await tokens.revoke(row)


@router.post("/auth/verify-email", status_code=204)
async def verify_email(
    data: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    user_id = await consume_token(db, data.token, "verify_email")
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")

    user = await db.get(User, user_id)
    user.is_verified = True
    await db.commit()

@router.post("/auth/forgot-password", status_code=202)
async def forgot_password(
    data: ForgotPasswordRequest,
    crud: Annotated[UserCrud, Depends(get_user_crud)],
    db: Annotated[AsyncSession, Depends(get_db)],
    arq: Annotated[ArqRedis, Depends(get_arq)],
) -> None:
    user = await crud.get_by_email(data.email)
    if user is not None:
        token = await create_token(db, user.id, "reset_password", ttl_minutes=30)
        await arq.enqueue_job("send_password_reset_email", user.email, token)

@router.post("/auth/reset-password", status_code=204)
async def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> None:
    user_id = await consume_token(db, data.token, "reset_password")
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")

    user = await db.get(User, user_id)
    user.hashed_password = hash_password(data.new_password)
    await db.commit()

    await tokens.revoke_all_for_user(user_id)