import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.db.models.one_time_token import OneTimeToken


async def create_token(session: AsyncSession, user_id: int, purpose: str, ttl_minutes: int) -> str:
    raw = secrets.token_urlsafe(32)
    token = OneTimeToken(
        user_id=user_id,
        token_hash=hash_token(raw),
        purpose=purpose,
        expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
    )
    session.add(token)
    await session.commit()
    return raw


async def consume_token(session: AsyncSession, raw: str, purpose: str) -> int | None:

    token_hash = hash_token(raw)

    result = await session.execute(
        select(OneTimeToken).where(
            OneTimeToken.token_hash == token_hash,
            OneTimeToken.purpose == purpose,
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None
    if token.used_at is not None:
        return None
    if token.expires_at < datetime.now(UTC):
        return None

    token.used_at = datetime.now(UTC)
    await session.commit()
    return token.user_id
