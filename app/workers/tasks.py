import io
import zipfile
from datetime import UTC, datetime

from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_storage
from app.core.config import get_settings
from app.core.email import get_sender
from app.db.models.entry import Entry
from app.db.models.export import Export

settings = get_settings()


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

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            filename = f"{entry.entry_date}-{entry.id}.md"
            content = (
                f"# {entry.title}\n\n"
                f"Date: {entry.entry_date}\n"
                f"Mood: {entry.mood}\n\n"
                f"{entry.content}\n"
            )
            zf.writestr(filename, content)

    blob_name = f"exports/export-{export_id}.zip"
    storage = get_storage()
    await storage.upload(blob_name, zip_buffer.getvalue(), "application/zip")

    export.status = "ready"
    export.file_path = blob_name
    export.completed_at = datetime.now(UTC)
    await session.commit()


async def export_entries(ctx, export_id: int, user_id: int) -> None:
    engine = create_async_engine(settings.database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await _export(session, export_id, user_id)
    await engine.dispose()


async def send_verification_email(ctx, email: str, token: str) -> None:
    sender = get_sender()
    link = f"{settings.base_url}/api/v1/auth/verify-email?token={token}"
    await sender.send(
        to=email,
        subject="Verify your email",
        body=f"Welcome. Confirm your address:\n\n{link}\n",
    )


async def send_password_reset_email(ctx, email: str, token: str) -> None:
    sender = get_sender()
    link = f"{settings.base_url}/api/v1/auth/reset-password?token={token}"
    await sender.send(
        to=email,
        subject="Reset your password",
        body=f"Reset your password:\n\n{link}\n\nThis link expires in 30 minutes.\n",
    )


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [export_entries, send_verification_email, send_password_reset_email]
