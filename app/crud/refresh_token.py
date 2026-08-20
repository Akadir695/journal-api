from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_token
from app.db.models.refresh_token import RefreshToken

settings = get_settings()


class RefreshTokenCrud:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, user_id: int, token: str) -> RefreshToken:
        row = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return row

    async def get_by_token(self, token: str) -> RefreshToken | None:
        result = await self._db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(token))
        )
        return result.scalar_one_or_none()

    async def revoke(self, row: RefreshToken) -> None:
        row.revoked_at = datetime.now(UTC)
        await self._db.commit()

    async def revoke_all_for_user(self, user_id: int) -> None:
        await self._db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._db.commit()
