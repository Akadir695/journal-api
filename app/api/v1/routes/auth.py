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
) -> UserRead:
    if await crud.get_by_email(data.email) is not None:
        raise ConflictError("Email already registered")
    if await crud.get_by_username(data.username) is not None:
        raise ConflictError("Username already taken")
    return await crud.create(data)


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
