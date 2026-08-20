from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.crud.user import UserCrud
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserRead

settings = get_settings()

router = APIRouter()


def get_user_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> UserCrud:
    return UserCrud(db)


@router.post("/auth/register", status_code=201)
async def register(
    data: UserCreate,
    crud: Annotated[UserCrud, Depends(get_user_crud)],
) -> UserRead:
    existing = await crud.get_by_email(data.email)
    if existing is not None:
        raise ConflictError("Email already registered")
    return await crud.create(data)


@router.post("/auth/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    crud: Annotated[UserCrud, Depends(get_user_crud)],
) -> Token:
    user = await crud.get_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    token = create_access_token(str(user.id), settings.access_token_expire_minutes)
    return Token(access_token=token)
