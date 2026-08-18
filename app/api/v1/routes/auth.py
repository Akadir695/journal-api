from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.crud.user import UserCrud
from app.db.session import get_db
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


def get_user_crud(db: Annotated[AsyncSession, Depends(get_db)]) -> UserCrud:
    return UserCrud(db)


@router.post("/auth/register", status_code=201)
async def register(
    data: UserCreate,
    crud: Annotated[UserCrud, Depends(get_user_crud)],
) -> UserRead:
    existing = await crud.get_by_email(data.email)
    if existing is not None:
        raise ConflictError("Email already registered")
    return await crud.create(data)
