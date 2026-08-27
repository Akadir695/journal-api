from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.entry import Entry
from app.schemas.entry import EntryCreate, EntryRead, Page, EntryUpdate
from sqlalchemy import select, update, func
from datetime import datetime, timezone, date
from app.db.models.tag import Tag

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

SORTABLE = {"date": Entry.entry_date, "mood": Entry.mood}

class SqlEntryCrud:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
    def base_query(self, user_id: int):
         return select(Entry).where(Entry.user_id == 
            user_id, Entry.deleted_at.is_(None))
   

    async def create(self, data: EntryCreate, user_id: int) -> EntryRead:
        entry = Entry(
            title=data.title,
            content=data.content,
            mood=data.mood,
            user_id=user_id,
            entry_date=data.entry_date,
        )
        entry.tags = await self._get_or_create_tags(data.tags, user_id)
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return EntryRead.model_validate(entry)

    async def get(self, entry_id: int, user_id: int) -> EntryRead | None:
        result = await self._db.execute(
            self.base_query(user_id).where(Entry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return None
        return EntryRead.model_validate(entry)

    async def list_all(self, user_id: int,  page: int, size: int, mood: 
        int | None = None, 
        date_from: date | None = None, date_to: date | None = None, sort: str = "date", q: str | None = None) -> Page[EntryRead]:  
              
        query = self.base_query(user_id)
        if mood is not None:
            query = query.where(Entry.mood == mood)
        if q:
            query = query.where(
                Entry.search_vector.op("@@")(func.websearch_to_tsquery("english", q))
            )
        if date_from is not None:
            query = query.where(Entry.entry_date >= date_from)
        if date_to is not None:
            query = query.where(Entry.entry_date <= date_to)
        count_result = await self._db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        result = await self._db.execute(
            query.limit(size).offset((page - 1) * size).order_by(SORTABLE[sort].desc())
        )
        entries = result.scalars().all()
        results = []
        for e in entries:
            results.append(EntryRead.model_validate(e))
        return Page(items=results, total=total, page=page, size=size)
    
    async def update(self, entry_id: int, user_id: int, data: EntryUpdate) -> EntryRead | None:
        stmt = select(Entry).where(
            Entry.id == entry_id,
            Entry.user_id == user_id,
            Entry.deleted_at.is_(None),
        )
        entry = (await self._db.execute(stmt)).scalar_one_or_none()
        if entry is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)

        await self._db.commit()
        await self._db.refresh(entry)
        return EntryRead.model_validate(entry)
    async def delete(self, entry_id: int, user_id: int) -> bool:
        result = await self._db.execute(
        update(Entry)
             .where(Entry.id == entry_id, Entry.user_id == user_id, Entry.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc))
        )
        
        await self._db.commit()
        return result.rowcount > 0
    async def restore(self, entry_id: int, user_id: int) -> bool:
        result = await self._db.execute(
        update(Entry)
             .where(Entry.id == entry_id, Entry.user_id == user_id, Entry.deleted_at.is_not(None))
            .values(deleted_at=None)
        )
        await self._db.commit()
        return result.rowcount > 0
         
    async def _get_or_create_tags(self, names: list[str], user_id: int) -> list[Tag]:
        if not names:
            return []
        lowered = [n.lower() for n in names]

        result = await self._db.execute(
            select(Tag).where(
                Tag.user_id == user_id,
                func.lower(Tag.name).in_(lowered),
            )
        )
        existing = result.scalars().all()
        found = {t.name.lower() for t in existing}
        new_tags = [Tag(name=n, user_id=user_id) for n in names if n.lower() not in found]

        for tag in new_tags:
            self._db.add(tag)
        return list(existing) + new_tags
        
