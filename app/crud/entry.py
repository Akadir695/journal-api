from datetime import UTC, datetime

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
