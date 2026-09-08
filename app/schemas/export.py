from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    file_path: str | None
    created_at: datetime
    completed_at: datetime | None
class ExportDownload(BaseModel):
    download_url: str
