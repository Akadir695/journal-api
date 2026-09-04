from datetime import date

from pydantic import BaseModel


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    last_entry_date: date | None


class MonthStatOut(BaseModel):
    month: int
    entries: int
    avg_mood: float | None
    words: int


class YearSummaryOut(BaseModel):
    year: int
    total_entries: int
    total_words: int
    months: list[MonthStatOut]
