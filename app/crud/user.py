from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.schemas.user import UserCreate, UserRead


class UserCrud:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, data: UserCreate) -> UserRead:  # ← same indent as __init__
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return UserRead.model_validate(user)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self._db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
