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


@lru_cache
def get_storage() -> Storage:
    """Build a storage client for wherever we are running.

    A connection string means local development against Azurite, which only
    understands account keys. Without one we are in Azure, where the managed
    identity means there is no key to hold.
    """
    settings = get_settings()
    return AzureBlobStorage(
        container=settings.azure_storage_container,
        connection_string=settings.azure_storage_connection_string,
        account_name=settings.azure_storage_account_name,
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
