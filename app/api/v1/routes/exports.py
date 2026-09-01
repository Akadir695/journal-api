from typing import Annotated

from arq import ArqRedis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_arq, get_current_user
from app.core.exceptions import NotFoundError
from app.db.models.export import Export
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.export import ExportRead

router = APIRouter()


@router.post("/exports", status_code=202)
async def create_export(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    arq: Annotated[ArqRedis, Depends(get_arq)],
) -> ExportRead:
    export = Export(user_id=current_user.id, status="pending")
    db.add(export)
    await db.commit()
    await db.refresh(export)

    await arq.enqueue_job("export_entries", export.id, current_user.id)

    return ExportRead.model_validate(export)


@router.get("/exports/{export_id}")
async def read_export(
    export_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportRead:
    export = await db.get(Export, export_id)
    if export is None or export.user_id != current_user.id:
        raise NotFoundError("Export not found")
    return ExportRead.model_validate(export)
