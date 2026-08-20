from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise UnauthorizedError("Could not validate credentials")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Could not validate credentials")

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("Could not validate credentials")

    return user
