from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.core.storage import AzureBlobStorage, Storage
from app.db.models.user import User
from app.db.session import get_db


def get_redis(request: Request):
    return request.app.state.redis


def get_arq(request: Request):
    return request.app.state.arq


from functools import lru_cache

@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    return AzureBlobStorage(
        settings.azure_storage_connection_string,
        settings.azure_storage_container,
    )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise UnauthorizedError("Could not validate credentials") from None

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Could not validate credentials")

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("Could not validate credentials")
    if not user.is_verified:
        raise ForbiddenError("Email address not verified")

    return user
