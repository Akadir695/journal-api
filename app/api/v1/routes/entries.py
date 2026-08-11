from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import NotFoundError
from app.crud.entry import EntryCrud
from app.schemas.entry import EntryCreate, EntryRead


def get_crud() -> EntryCrud:
    return crud


router = APIRouter()
crud = EntryCrud()


@router.get("/entries/{entry_id}")
async def read_entry(entry_id: int, crud: Annotated[EntryCrud, Depends(get_crud)]) -> EntryRead:
    entry = crud.get(entry_id)
    if entry is None:
        raise NotFoundError("Entry not found")
    return entry


@router.get("/entries")
async def list_entries(
    crud: Annotated[EntryCrud, Depends(get_crud)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: str | None = None,
) -> list[EntryRead]:
    return crud.list_all(limit)


@router.post("/entries", status_code=201)
async def create_entry(
    entry: EntryCreate,
    crud: Annotated[EntryCrud, Depends(get_crud)],
) -> EntryRead:
    return crud.create(entry)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: int, crud: Annotated[EntryCrud, Depends(get_crud)]) -> None:
    if not crud.delete_entry(entry_id):
        raise NotFoundError("Entry not found")
