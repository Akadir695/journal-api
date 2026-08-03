from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.entry import EntryCreate, EntryRead

router = APIRouter()

@router.get("/entries/{entry_id}")
async def list_entry(entry_id: int) -> dict[str, int]:
    return {"entry_id": entry_id}
  
@router.get("/entries")
async def list_entries(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: str | None = None,
) -> dict[str, int | str | None]:
    return {"limit": limit, "mood": mood}
  
@router.post("/entries", status_code=201)
async def create_entry(entry: EntryCreate) -> EntryRead:
    return EntryRead(
        id=1,
        title=entry.title,
        content=entry.content,
        mood=entry.mood,
        entry_date=entry.entry_date,
        created_at=datetime.now(timezone.utc),
    )