from datetime import UTC, datetime
from typing import Annotated

from arq import ArqRedis
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_arq
from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.crud.one_time_token import consume_token, create_token
from app.crud.refresh_token import RefreshTokenCrud
from app.crud.user import UserCrud
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import (
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
    VerifyEmailRequest,
)

settings = get_settings()

router = APIRouter()


def get_user_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> UserCrud:
    return UserCrud(db)


def get_refresh_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> RefreshTokenCrud:
    return RefreshTokenCrud(db)


@router.post(
    "/auth/register",
    status_code=201,
    summary="Register a new account",
    response_description="The created user",
    responses={
        409: {"description": "Email already registered, or username taken"},
        422: {"description": "Validation failed"},
    },
)
async def register(
    data: UserCreate,
    crud: Annotated[UserCrud, Depends(get_user_crud)],
    db: Annotated[AsyncSession, Depends(get_db)],
    arq: Annotated[ArqRedis, Depends(get_arq)],
) -> UserRead:
    """Create an account and send a verification email.

    The verification email is queued in the background, so this returns before
    it is sent. The link inside is valid for 24 hours.
    """
    if await crud.get_by_email(data.email) is not None:
        raise ConflictError("Email already registered")
    if await crud.get_by_username(data.username) is not None:
        raise ConflictError("Username already taken")

    created = await crud.create(data)
    token = await create_token(db, created.id, "verify_email", ttl_minutes=1440)
    await arq.enqueue_job("send_verification_email", created.email, token)
    return created


@router.post(
    "/auth/login",
    summary="Log in",
    response_description="An access token and a refresh token",
    responses={401: {"description": "Incorrect email or password"}},
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    crud: Annotated[UserCrud, Depends(get_user_crud)],
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> Token:
    """Exchange email and password for a token pair.

    Send credentials as form data, not JSON — this follows the OAuth2 password
    flow, so the email goes in the `username` field.

    The access token is short-lived; use the refresh token to get a new one.
    """
    user = await crud.get_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")

    access = create_access_token(str(user.id), settings.access_token_expire_minutes)
    refresh = create_refresh_token()
    await tokens.create(user.id, refresh)

    return Token(access_token=access, refresh_token=refresh)


@router.post(
    "/auth/refresh",
    summary="Exchange a refresh token for a new pair",
    response_description="A new access token and a new refresh token",
    responses={401: {"description": "Refresh token is invalid, expired, or already used"}},
)
async def refresh(
    data: RefreshRequest,
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> Token:
    """Rotate a refresh token.

    Each refresh token can be used **once**. Using it returns a new pair and
    revokes the old one.

    If an already-revoked token is presented, every refresh token for that user
    is revoked immediately — a reused token means it was probably stolen, so the
    safe response is to log the account out everywhere.
    """
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


@router.post(
    "/auth/logout",
    status_code=204,
    summary="Revoke a refresh token",
)
async def logout(
    data: RefreshRequest,
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> None:
    """Revoke a refresh token.

    Always returns 204, whether the token existed or not. Logging out twice is
    not an error.
    """
    row = await tokens.get_by_token(data.refresh_token)
    if row is not None and row.revoked_at is None:
        await tokens.revoke(row)


@router.post(
    "/auth/verify-email",
    status_code=204,
    summary="Verify an email address",
    responses={401: {"description": "Token is invalid, expired, or already used"}},
)
async def verify_email(
    data: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Confirm an email address using the code from the verification email.

    Tokens are single-use and expire after 24 hours. This API is JSON-only, so
    a client sends the code here rather than the user following a link.
    """
    user_id = await consume_token(db, data.token, "verify_email")
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")

    user = await db.get(User, user_id)
    user.is_verified = True
    await db.commit()


@router.post(
    "/auth/forgot-password",
    status_code=202,
    summary="Request a password reset email",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    crud: Annotated[UserCrud, Depends(get_user_crud)],
    db: Annotated[AsyncSession, Depends(get_db)],
    arq: Annotated[ArqRedis, Depends(get_arq)],
) -> None:
    """Send a password reset link, if the address belongs to an account.

    Always returns 202, whether or not the email is registered. This is
    deliberate — a different response for unknown addresses would let anyone
    test which emails have accounts here.

    The link is valid for 30 minutes.
    """
    user = await crud.get_by_email(data.email)
    if user is not None:
        token = await create_token(db, user.id, "reset_password", ttl_minutes=30)
        await arq.enqueue_job("send_password_reset_email", user.email, token)


@router.post(
    "/auth/reset-password",
    status_code=204,
    summary="Set a new password using a reset token",
    responses={401: {"description": "Token is invalid, expired, or already used"}},
)
async def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    tokens: Annotated[RefreshTokenCrud, Depends(get_refresh_crud)],
) -> None:
    """Set a new password.

    Tokens are single-use and expire after 30 minutes. On success every refresh
    token for the account is revoked, so any existing sessions are logged out.
    """
    user_id = await consume_token(db, data.token, "reset_password")
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")

    user = await db.get(User, user_id)
    user.hashed_password = hash_password(data.new_password)
    await db.commit()

    await tokens.revoke_all_for_user(user_id)
