from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.crud.entry import SqlEntryCrud
from app.db.session import get_db
from app.schemas.entry import EntryCreate, EntryRead
from app.api.deps import get_current_user
from app.db.models.user import User


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
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: str | None = None,
) -> list[EntryRead]:
    return await crud.list_all(limit, current_user.id)


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
    
    
    