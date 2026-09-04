from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


class AttachmentCreate(BaseModel):
    filename: str
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(gt=0, le=MAX_SIZE_BYTES)


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int | None
    content_type: str | None
    size_bytes: int | None
    status: str
    created_at: datetime
    confirmed_at: datetime | None


class AttachmentDownload(BaseModel):
    url: str
    expires_in: int


class AttachmentUploadResponse(BaseModel):
    attachment: AttachmentRead
    upload_url: str
    expires_in: int
