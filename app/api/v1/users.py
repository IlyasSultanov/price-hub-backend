from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.depends import get_user_manager
from app.core.security import require_roles
from app.schemas import UserRead, UserRoleUpdate
from app.service.auth import UserManager
from app.utils import UserRole

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_roles(UserRole.SYSTEM_ADMIN))],
)


@router.get("", response_model=list[UserRead])
async def list_users(
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
) -> list[UserRead]:
    users = await user_manager.list_users()
    return [UserRead(**user) for user in users]


@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
) -> UserRead:
    user = await user_manager.update_user_role(user_id, payload.role)
    return UserRead(**user)
