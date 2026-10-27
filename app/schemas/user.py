from pydantic import BaseModel

from ..utils import UserRole


class UserRead(BaseModel):
    id: str
    username: str
    email: str | None
    first_name: str | None
    last_name: str | None
    roles: list[UserRole]
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: UserRole
