from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2000)
    mood: int = Field(ge=1, le=5)
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
