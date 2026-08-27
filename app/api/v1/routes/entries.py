from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.crud.entry import SqlEntryCrud
from app.db.session import get_db
from app.schemas.entry import EntryCreate, EntryRead,  Page, EntryUpdate
from app.api.deps import get_current_user
from app.db.models.user import User
from datetime import date
from typing import Literal


def get_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> SqlEntryCrud:
    return SqlEntryCrud(db)


router = APIRouter()



@router.post("/entries", status_code=201)
async def create_entry(
    entry: EntryCreate,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EntryRead:
    return await crud.create(entry, current_user.id)

@router.get("/entries/{entry_id}")
async def read_entry(
    entry_id: int,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EntryRead:
    entry = await crud.get(entry_id, current_user.id)
    if entry is None:
      raise NotFoundError("Entry not found")
    return entry


@router.get("/entries")
async def list_entries(
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: Annotated[int | None, Query(ge=1, le=5)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: Literal["date", "mood"] = "date",
    q: str | None = None
) -> Page[EntryRead]:
    return await crud.list_all(current_user.id, page, size, mood, date_from, date_to,  sort=sort, q=q)
    
@router.patch("/entries/{entry_id}")
async def update_entry(
    entry_id: int,
    data: EntryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
) -> EntryRead:
    entry = await crud.update(entry_id, current_user.id, data)
    if entry is None:
        raise NotFoundError("Entry not found")
    return entry

@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: int,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if not await crud.delete(entry_id, current_user.id):
        raise NotFoundError("Entry not found")
@router.post("/entries/{entry_id}/restore", status_code=204)
async def restore(entry_id: int, 
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if not await crud.restore(entry_id, current_user.id):
      raise NotFoundError("Entry not found")
    
    
    