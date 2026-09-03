from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    AttachmentRead,
    AttachmentUploadResponse,
)

router = APIRouter()

UPLOAD_URL_TTL = 300
READ_URL_TTL = 300


@router.post("/attachments", status_code=201)
async def create_attachment(
    payload: AttachmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> AttachmentUploadResponse:
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
        upload_url=storage.upload_url(
            attachment.blob_path, payload.content_type, UPLOAD_URL_TTL
        ),
        expires_in=UPLOAD_URL_TTL,
    )


@router.post("/attachments/{attachment_id}/confirm")
async def confirm_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> AttachmentRead:
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
    attachment.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(attachment)

    return AttachmentRead.model_validate(attachment)


@router.get("/attachments/{attachment_id}")
async def read_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> dict[str, str | int]:
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None or attachment.user_id != current_user.id:
        raise NotFoundError("Attachment not found")
    if attachment.status != "ready":
        raise NotFoundError("Attachment not ready")

    return {
        "url": storage.read_url(attachment.blob_path, READ_URL_TTL),
        "expires_in": READ_URL_TTL,
    }
@router.get("/attachments")
async def list_attachments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttachmentRead]:
    result = await db.execute(
        select(Attachment).where(Attachment.user_id == current_user.id)
    )
    return [AttachmentRead.model_validate(a) for a in result.scalars()]