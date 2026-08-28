from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entry import Entry
from app.schemas.stats import StreakOut, YearSummaryOut, MonthStatOut
from datetime import date, timedelta


class StatsCrud:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_streaks(self, user_id: int, today: date) -> StreakOut:
        days = (
            select(Entry.entry_date)
            .where(Entry.user_id == user_id, Entry.deleted_at.is_(None))
            .distinct()
            .cte("days")
        )

        row_num = func.row_number().over(order_by=days.c.entry_date)

        grouped = select(
            days.c.entry_date,
            (days.c.entry_date - cast(row_num, Integer)).label("grp"),
        ).cte("grouped")

        streaks = (
            select(
                func.count().label("length"),
                func.max(grouped.c.entry_date).label("ended_on"),
            )
            .group_by(grouped.c.grp)
            .cte("streaks")
        )

        rows = (await self._db.execute(select(streaks))).all()
        if not rows:
            return StreakOut(
                current_streak=0,
                longest_streak=0,
                last_entry_date=None,
            )
        yesterday = today - timedelta(days=1)
        current_streak = next(
            (length for length, ended_on in rows if ended_on in (today, yesterday)),
            0,
        )
        longest_streak = max(length for length, _ in rows)
        last_entry_date = max(ended_on for _, ended_on in rows)

        return StreakOut(
            current_streak=current_streak,
            longest_streak=longest_streak,
            last_entry_date=last_entry_date,
        )

    async def get_year_summary(self, user_id: int, year: int) -> YearSummaryOut:
        month = func.extract("month", Entry.entry_date).label("month")
        words = func.coalesce(
            func.sum(func.array_length(func.string_to_array(Entry.content, " "), 1)),
            0,
        ).label("words")

        stmt = (
            select(
                month,
                func.count().label("entries"),
                func.avg(Entry.mood).label("avg_mood"),
                words,
            )
            .where(
                Entry.user_id == user_id,
                Entry.deleted_at.is_(None),
                func.extract("year", Entry.entry_date) == year,
            )
            .group_by(month)
            .order_by(month)
        )

        rows = (await self._db.execute(stmt)).all()
        by_month = {int(r.month): r for r in rows}

        months = [
            MonthStatOut(
                month=m,
                entries=by_month[m].entries if m in by_month else 0,
                avg_mood=(
                    float(by_month[m].avg_mood)
                    if m in by_month and by_month[m].avg_mood is not None
                    else None
                ),
                words=by_month[m].words if m in by_month else 0,
            )
            for m in range(1, 13)
        ]

        return YearSummaryOut(
            year=year,
            total_entries=sum(m.entries for m in months),
            total_words=sum(m.words for m in months),
            months=months,
        )
