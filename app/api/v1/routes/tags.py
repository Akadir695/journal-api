from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.responses import AUTH_ERRORS
from app.crud.tag import TagCrud
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.tag import TagRead

router = APIRouter()


def get_tag_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> TagCrud:
    return TagCrud(db)


@router.get(
    "/tags",
    summary="List your tags",
    response_description="Every tag used on your entries",
    responses={**AUTH_ERRORS},
)
async def list_tags(
    crud: Annotated[TagCrud, Depends(get_tag_crud)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[TagRead]:
    """Return the tags belonging to the current user.

    Tags are scoped per user, so two people can use the same tag name
    independently.
    """
    return await crud.list_all(current_user.id)
