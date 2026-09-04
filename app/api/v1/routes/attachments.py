from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_storage
from app.core.exceptions import ConflictError, NotFoundError
from app.core.storage import Storage
from app.db.models.attachment import Attachment
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.attachment import (
    ALLOWED_TYPES,
    MAX_SIZE_BYTES,
    AttachmentCreate,
    AttachmentDownload,
    AttachmentRead,
    AttachmentUploadResponse,
)

router = APIRouter()

UPLOAD_URL_TTL = 300
READ_URL_TTL = 300


@router.post(
    "/attachments",
    status_code=201,
    summary="Start an upload",
    response_description="The pending attachment and a signed upload URL",
    responses={
        401: {"description": "Missing or invalid credentials"},
        422: {"description": "Unsupported content type, or file too large"},
    },
)
async def create_attachment(
    payload: AttachmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> AttachmentUploadResponse:
    """Reserve an attachment and get a short-lived URL to upload to.

    The file is **not** sent to this API. Upload it directly to the returned
    `upload_url` with a PUT request, then call the confirm endpoint.

    The PUT must include two headers:

    - `x-ms-blob-type: BlockBlob`
    - `Content-Type` matching the type declared here

    The URL expires after `expires_in` seconds. Request a new one if it lapses.
    """
    suffix = Path(payload.filename).suffix.lower()
    attachment = Attachment(
        user_id=current_user.id,
        blob_path=f"{current_user.id}/{uuid4().hex}{suffix}",
        status="pending",
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return AttachmentUploadResponse(
        attachment=AttachmentRead.model_validate(attachment),
        upload_url=storage.upload_url(attachment.blob_path, payload.content_type, UPLOAD_URL_TTL),
        expires_in=UPLOAD_URL_TTL,
    )


@router.get(
    "/attachments",
    summary="List your attachments",
    response_description="Every attachment belonging to the current user",
    responses={401: {"description": "Missing or invalid credentials"}},
)
async def list_attachments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttachmentRead]:
    """Return your attachments, newest first.

    Includes both `pending` and `ready` records. Pending ones are uploads that
    were started but never confirmed.
    """
    result = await db.execute(
        select(Attachment)
        .where(Attachment.user_id == current_user.id)
        .order_by(Attachment.created_at.desc())
    )
    return [AttachmentRead.model_validate(a) for a in result.scalars()]


@router.post(
    "/attachments/{attachment_id}/confirm",
    summary="Confirm an upload completed",
    response_description="The attachment, now ready",
    responses={
        401: {"description": "Missing or invalid credentials"},
        404: {"description": "No such attachment, or it belongs to another user"},
        409: {"description": "Nothing was uploaded, or the file does not match"},
    },
)
async def confirm_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> AttachmentRead:
    """Mark an attachment ready once its upload has finished.

    Reads the file's real size and content type back from storage rather than
    trusting what was declared at creation. A mismatch is rejected here and the
    uploaded file deleted.

    Safe to call more than once — an already-confirmed attachment is returned
    unchanged.
    """
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None or attachment.user_id != current_user.id:
        raise NotFoundError("Attachment not found")

    if attachment.status == "ready":
        return AttachmentRead.model_validate(attachment)

    props = await storage.get_properties(attachment.blob_path)
    if props is None:
        raise ConflictError("Upload not completed")

    if props.content_type not in ALLOWED_TYPES or props.size > MAX_SIZE_BYTES:
        await storage.delete(attachment.blob_path)
        raise ConflictError("Uploaded file does not match what was declared")

    attachment.content_type = props.content_type
    attachment.size_bytes = props.size
    attachment.status = "ready"
    attachment.confirmed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(attachment)

    return AttachmentRead.model_validate(attachment)


@router.get(
    "/attachments/{attachment_id}",
    summary="Get a link to download an attachment",
    response_description="A short-lived signed URL for the file",
    responses={
        401: {"description": "Missing or invalid credentials"},
        404: {"description": "Not found, not yours, or not yet confirmed"},
    },
)
async def read_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> AttachmentDownload:
    """Return a signed URL for the file itself.

    The bytes are served by storage, not this API. The URL expires after
    `expires_in` seconds, and a fresh one is issued on every call — so fetch
    it when you need it rather than caching it.
    """
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None or attachment.user_id != current_user.id:
        raise NotFoundError("Attachment not found")
    if attachment.status != "ready":
        raise NotFoundError("Attachment not ready")

    return AttachmentDownload(
        url=storage.read_url(attachment.blob_path, READ_URL_TTL),
        expires_in=READ_URL_TTL,
    )
