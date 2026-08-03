from datetime import datetime, timezone
from typing import Annotated
from app.crud.entry import EntryCrud


from fastapi import APIRouter, Query, HTTPException

from app.schemas.entry import EntryCreate, EntryRead

router = APIRouter()
crud = EntryCrud()
@router.get("/entries/{entry_id}")
async def read_entry(entry_id: int) -> EntryRead:
  entry = crud.get(entry_id)
  if entry is None:
    raise HTTPException(status_code=404, detail="Entry not found")
  return entry
    
  
@router.get("/entries")
async def list_entries(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: str | None = None,
) -> list[EntryRead]:
    return crud.list_all(limit)

@router.post("/entries", status_code=201)
async def create_entry(entry: EntryCreate) -> EntryRead:
    return crud.create(entry)
  
@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: int) -> None:
    if not crud.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")