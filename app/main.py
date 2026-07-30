from typing import Annotated
from fastapi import FastAPI, Query
from app.schemas.entry import EntryCreate

app = FastAPI(
    title="journal api",
    description="this is journal api where people use to journal their ideas",
    version="0.1.0",
)
@app.get("/health")
async def root() -> dict[str, str]:
    return {"status": "ok"}
@app.get("/entries/{entry_id}")
async def list_entry(entry_id: int) -> dict[str, int]:
    return {"entry_id": entry_id}
  
@app.get("/entries")
async def list_entries(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: str | None = None,
) -> dict[str, int | str | None]:
    return {"limit": limit, "mood": mood}
  
@app.post("/entries", status_code=201)
async def create_entry(entry: EntryCreate) -> EntryCreate:
  return entry

  
