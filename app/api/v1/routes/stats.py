from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.api.deps import get_current_user, get_redis
from app.core.cache import cache_get, cache_set
from app.core.config import get_settings


from app.crud.stats import StatsCrud
from app.db.session import get_db
from app.schemas.stats import StreakOut, YearSummaryOut
from app.api.deps import get_current_user
from app.db.models.user import User
from datetime import datetime, UTC

settings = get_settings()
router = APIRouter()


def get_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> StatsCrud:
    return StatsCrud(db)


@router.get("/streak", response_model=StreakOut)
async def get_streak(
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[StatsCrud, Depends(get_crud)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> StreakOut:
    key = f"stats:streak:user:{current_user.id}"

    cached = await cache_get(redis, key)
    if cached is not None:
        return StreakOut.model_validate_json(cached)

    today = datetime.now(UTC).date()
    result = await crud.get_streaks(current_user.id, today)
    await cache_set(redis, key, result.model_dump_json(), settings.cache_ttl_seconds)
    return result


@router.get("/summary", response_model=YearSummaryOut)
async def get_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[StatsCrud, Depends(get_crud)],
    redis: Annotated[Redis, Depends(get_redis)],
    year: int = Query(default=..., ge=2000, le=2100),
) -> YearSummaryOut:
    key = f"stats:summary:{year}:user:{current_user.id}"
    cached = await cache_get(redis, key)
    if cached is not None:
        return YearSummaryOut.model_validate_json(cached)
    result = await crud.get_year_summary(current_user.id, year)
    await cache_set(redis, key, result.model_dump_json(), settings.cache_ttl_seconds)
    return result
