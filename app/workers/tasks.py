import zipfile
from datetime import UTC, datetime
from pathlib import Path

from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models.entry import Entry
from app.db.models.export import Export

settings = get_settings()
EXPORT_DIR = Path(settings.export_dir).resolve()


async def _export(session: AsyncSession, export_id: int, user_id: int) -> None:
    export = await session.get(Export, export_id)
    if export is None or export.status == "ready":
        return

    result = await session.execute(
        select(Entry)
        .where(Entry.user_id == user_id, Entry.deleted_at.is_(None))
        .order_by(Entry.entry_date)
    )
    entries = result.scalars().all()

    EXPORT_DIR.mkdir(exist_ok=True)
    path = EXPORT_DIR / f"export-{export_id}.zip"

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            filename = f"{entry.entry_date}-{entry.id}.md"
            content = (
                f"# {entry.title}\n\n"
                f"Date: {entry.entry_date}\n"
                f"Mood: {entry.mood}\n\n"
                f"{entry.content}\n"
            )
            zf.writestr(filename, content)

    export.status = "ready"
    export.file_path = str(path)
    export.completed_at = datetime.now(UTC)
    await session.commit()


async def export_entries(ctx, export_id: int, user_id: int) -> None:
    engine = create_async_engine(settings.database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await _export(session, export_id, user_id)
    await engine.dispose()


class WorkerSettings:
    functions = [export_entries]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
