from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entry import Entry
from app.schemas.entry import EntryCreate, EntryRead


class EntryCrud:
    def __init__(self) -> None:
        self._entries: dict[int, EntryRead] = {}
        self._next_id = 1

    def create(self, data: EntryCreate) -> EntryRead:
        entry = EntryRead(
            id=self._next_id,
            title=data.title,
            content=data.content,
            mood=data.mood,
            entry_date=data.entry_date,
            created_at=datetime.now(UTC),
        )
        self._entries[entry.id] = entry
        self._next_id += 1
        return entry

    def get(self, entry_id: int) -> EntryRead | None:
        return self._entries.get(entry_id)

    def list_all(self, limit: int) -> list[EntryRead]:
        return list(self._entries.values())[:limit]

    def delete_entry(self, entry_id: int) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False


class SqlEntryCrud:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, data: EntryCreate, user_id: int) -> EntryRead:
        entry = Entry(
            title=data.title,
            content=data.content,
            mood=data.mood,
            user_id=user_id,
            entry_date=data.entry_date,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return EntryRead.model_validate(entry)

    async def get(self, entry_id: int, user_id: int) -> EntryRead | None:
        result = await self._db.execute(
            select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return None
        return EntryRead.model_validate(entry)

    async def list_all(self, limit: int, user_id: int) -> list[EntryRead]:
        result = await self._db.execute(
            select(Entry).where(Entry.user_id == user_id).limit(limit)
        )
        entries = result.scalars().all()
        results = []
        for e in entries:
            results.append(EntryRead.model_validate(e))
        return results

    async def delete(self, entry_id: int, user_id: int) -> bool:
        result = await self._db.execute(
            select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        await self._db.delete(entry)
        await self._db.commit()
        return True
