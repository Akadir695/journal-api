from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.crud.entry import SqlEntryCrud
from app.db.session import get_db
from app.schemas.entry import EntryCreate, EntryRead


def get_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> SqlEntryCrud:
    return SqlEntryCrud(db)


router = APIRouter()


@router.get("/entries/{entry_id}")
async def read_entry(entry_id: int, crud: Annotated[SqlEntryCrud, Depends(get_crud)]) -> EntryRead:
    entry = await crud.get(entry_id)
    if entry is None:
        raise NotFoundError("Entry not found")
    return entry


@router.get("/entries")
async def list_entries(
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: str | None = None,
) -> list[EntryRead]:
    return await crud.list_all(limit)


@router.post("/entries", status_code=201)
async def create_entry(
    entry: EntryCreate,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
) -> EntryRead:
    return await crud.create(entry)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: int, crud: Annotated[SqlEntryCrud, Depends(get_crud)]) -> None:
    if not await crud.delete(entry_id):
        raise NotFoundError("Entry not found")
