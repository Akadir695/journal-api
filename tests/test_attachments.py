from app.core.storage import BlobProperties
from urllib.parse import urlparse


def _path_from(upload_url: str) -> str:
    return urlparse(upload_url).path.lstrip("/")

async def _create(auth_client, **overrides):
    payload = {
        "filename": "cat.png",
        "content_type": "image/png",
        "size_bytes": 100,
    } | overrides
    return await auth_client.post("/api/v1/attachments", json=payload)


async def test_create_returns_pending_and_upload_url(auth_client, storage):
    response = await _create(auth_client)

    assert response.status_code == 201
    body = response.json()
    assert body["attachment"]["status"] == "pending"
    assert body["attachment"]["content_type"] is None
    assert "upload_url" in body


async def test_create_rejects_unsupported_type(auth_client, storage):
    response = await _create(auth_client, content_type="application/pdf")
    assert response.status_code == 422


async def test_create_rejects_oversized_file(auth_client, storage):
    response = await _create(auth_client, size_bytes=50 * 1024 * 1024)
    assert response.status_code == 422


async def test_confirm_fails_when_nothing_was_uploaded(auth_client, storage):
    attachment_id = (await _create(auth_client)).json()["attachment"]["id"]

    response = await auth_client.post(f"/api/v1/attachments/{attachment_id}/confirm")

    assert response.status_code == 409


async def test_confirm_reads_properties_from_storage(auth_client, storage, session):
    created = (await _create(auth_client)).json()
    attachment_id = created["attachment"]["id"]
    path = _path_from(created["upload_url"])
    storage.blobs[path] = BlobProperties(size=70, content_type="image/png")

    response = await auth_client.post(f"/api/v1/attachments/{attachment_id}/confirm")

    body = response.json()
    assert body["status"] == "ready"
    assert body["size_bytes"] == 70
    assert body["confirmed_at"] is not None


async def test_confirm_rejects_file_that_does_not_match_declaration(
    auth_client, storage
):
    created = (await _create(auth_client)).json()
    attachment_id = created["attachment"]["id"]
    path = _path_from(created["upload_url"])
    storage.blobs[path] = BlobProperties(size=70, content_type="application/pdf")

    response = await auth_client.post(f"/api/v1/attachments/{attachment_id}/confirm")

    assert response.status_code == 409
    assert path in storage.deleted


async def test_confirm_is_idempotent(auth_client, storage):
    created = (await _create(auth_client)).json()
    attachment_id = created["attachment"]["id"]
    storage.blobs[_path_from(created["upload_url"])] = BlobProperties(
        size=70, content_type="image/png"
    )

    first = await auth_client.post(f"/api/v1/attachments/{attachment_id}/confirm")
    second = await auth_client.post(f"/api/v1/attachments/{attachment_id}/confirm")

    assert first.json()["confirmed_at"] == second.json()["confirmed_at"]


async def test_read_is_not_available_before_confirm(auth_client, storage):
    attachment_id = (await _create(auth_client)).json()["attachment"]["id"]

    response = await auth_client.get(f"/api/v1/attachments/{attachment_id}")

    assert response.status_code == 404