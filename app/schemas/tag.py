from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    color: str | None
