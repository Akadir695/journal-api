from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.tag import TagRead

class EntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2000)
    mood: int = Field(ge=1, le=5)
    tags: list[str] = []
    entry_date: date

    @field_validator("title", "content")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("cannot be blank")
        return stripped


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    mood: int
    entry_date: date
    created_at: datetime
    tags: list[TagRead] = []

class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int     
class EntryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    mood: int | None = None
    entry_date: date | None = None
    tags: list[str] | None = None

                    