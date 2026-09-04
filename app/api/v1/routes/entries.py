from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis
from app.api.responses import AUTH_ERRORS, NOT_FOUND
from app.core.cache import cache_delete_user_stats
from app.core.exceptions import NotFoundError
from app.crud.entry import SqlEntryCrud
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.entry import EntryCreate, EntryRead, EntryUpdate, Page


def get_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> SqlEntryCrud:
    return SqlEntryCrud(db)


router = APIRouter()


@router.post(
    "/entries",
    status_code=201,
    summary="Create an entry",
    response_description="The created entry",
    responses={**AUTH_ERRORS, 422: {"description": "Validation failed"}},
)
async def create_entry(
    entry: EntryCreate,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> EntryRead:
    """Create a journal entry owned by the current user."""
    created = await crud.create(entry, current_user.id)
    await cache_delete_user_stats(redis, current_user.id)
    return created


@router.get(
    "/entries",
    summary="List your entries",
    response_description="A page of entries, newest first",
    responses={**AUTH_ERRORS},
)
async def list_entries(
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    mood: Annotated[int | None, Query(ge=1, le=5)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: Literal["date", "mood"] = "date",
    q: str | None = None,
) -> Page[EntryRead]:
    """Return your entries, paginated.

    Deleted entries are excluded. Filter by mood or date range, sort by date or
    mood, and search entry text with `q`.
    """
    return await crud.list_all(
        current_user.id, page, size, mood, date_from, date_to, sort=sort, q=q
    )


@router.get(
    "/entries/{entry_id}",
    summary="Get an entry",
    response_description="The entry",
    responses={**AUTH_ERRORS, **NOT_FOUND},
)
async def read_entry(
    entry_id: int,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EntryRead:
    """Return one of your entries.

    Entries belonging to another user return 404 rather than 403, so the
    endpoint does not reveal which ids exist.
    """
    entry = await crud.get(entry_id, current_user.id)
    if entry is None:
        raise NotFoundError("Entry not found")
    return entry


@router.patch(
    "/entries/{entry_id}",
    summary="Update an entry",
    response_description="The updated entry",
    responses={
        **AUTH_ERRORS,
        **NOT_FOUND,
        422: {"description": "Validation failed"},
    },
)
async def update_entry(
    entry_id: int,
    data: EntryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
) -> EntryRead:
    """Update an entry. Only the fields you send are changed."""
    entry = await crud.update(entry_id, current_user.id, data)
    if entry is None:
        raise NotFoundError("Entry not found")
    await cache_delete_user_stats(redis, current_user.id)
    return entry


@router.delete(
    "/entries/{entry_id}",
    status_code=204,
    summary="Delete an entry",
    responses={**AUTH_ERRORS, **NOT_FOUND},
)
async def delete_entry(
    entry_id: int,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    """Soft-delete an entry.

    The entry is hidden from listings but not removed from the database, so it
    can be brought back with the restore endpoint.
    """
    if not await crud.delete(entry_id, current_user.id):
        raise NotFoundError("Entry not found")
    await cache_delete_user_stats(redis, current_user.id)


@router.post(
    "/entries/{entry_id}/restore",
    status_code=204,
    summary="Restore a deleted entry",
    responses={**AUTH_ERRORS, **NOT_FOUND},
)
async def restore_entry(
    entry_id: int,
    crud: Annotated[SqlEntryCrud, Depends(get_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    """Undo a soft delete, making the entry visible again."""
    if not await crud.restore(entry_id, current_user.id):
        raise NotFoundError("Entry not found")
    await cache_delete_user_stats(redis, current_user.id)
