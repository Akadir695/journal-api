from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.responses import AUTH_ERRORS
from app.db.models.user import User
from app.schemas.user import UserRead

router = APIRouter()


@router.get(
    "/users/me",
    summary="Get the current user",
    response_description="The authenticated user's profile",
    responses={**AUTH_ERRORS},
)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Return the account belonging to the access token used for this request.

    Useful for confirming a token is still valid and which user it belongs to.
    """
    return current_user
