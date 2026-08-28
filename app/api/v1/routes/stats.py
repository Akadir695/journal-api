from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.stats import StatsCrud
from app.db.session import get_db
from app.schemas.stats import StreakOut, YearSummaryOut
from app.api.deps import get_current_user
from app.db.models.user import User
from datetime import datetime, UTC

router = APIRouter()


def get_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> StatsCrud:
    return StatsCrud(db)


@router.get("/streak", response_model=StreakOut)
async def get_streak(
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[StatsCrud, Depends(get_crud)],
) -> StreakOut:
    today = datetime.now(UTC).date()
    return await crud.get_streaks(current_user.id, today)


@router.get("/summary", response_model=YearSummaryOut)
async def get_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[StatsCrud, Depends(get_crud)],
    year: int = Query(default=..., ge=2000, le=2100),
) -> YearSummaryOut:
    return await crud.get_year_summary(current_user.id, year)
