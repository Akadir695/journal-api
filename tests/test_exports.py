from pathlib import Path

from sqlalchemy import select

from app.db.models.export import Export
from app.db.models.user import User
from app.workers.tasks import _export


async def test_export_creates_zip(auth_client, session):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )

    result = await session.execute(select(User).where(User.email == "tester@test.com"))
    user = result.scalar_one()

    export = Export(user_id=user.id, status="pending")
    session.add(export)
    await session.commit()

    await _export(session, export.id, user.id)

    assert export.status == "ready"
    assert export.file_path is not None
    assert Path(export.file_path).exists()

    Path(export.file_path).unlink()


async def test_export_is_idempotent(auth_client, session):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )

    result = await session.execute(select(User).where(User.email == "tester@test.com"))
    user = result.scalar_one()

    export = Export(user_id=user.id, status="pending")
    session.add(export)
    await session.commit()
    await _export(session, export.id, user.id)
    first_completed = export.completed_at

    await _export(session, export.id, user.id)
    assert export.completed_at == first_completed
    Path(export.file_path).unlink()


async def test_create_export_returns_202(auth_client, arq_client):
    response = await auth_client.post("/api/v1/exports")

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert any(name == "export_entries" for name, _ in arq_client.jobs)
