from typing import Annotated

from app.api.deps import get_current_user
from app.db.models.tag import Tag
from app.schemas.tag import TagRead
from app.crud.tag  import TagCrud
from fastapi import APIRouter,  Depends
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User


router = APIRouter()
def get_tag_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> TagCrud:
    return TagCrud(db)

@router.get("/tags")
async def list_tags(
    crud: Annotated[TagCrud, Depends(get_tag_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[TagRead]:
    return await crud.list_all(current_user.id)
  