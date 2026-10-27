from fastapi import Depends

from ...utils import UserRole
from .keycloak_manager import KeycloakManager, keycloak_manager_dependency


class UserManager:
    """Admin-facing user operations (FR-8.1: system_admin manages users).

    A thin layer over `KeycloakManager` — price-hub keeps no local user
    table (identity and roles live entirely in Keycloak; see
    `app.core.security` for how a request's JWT is turned into a
    `Principal`), so there's no local profile to sync here.
    """

    def __init__(self, keycloak: KeycloakManager):
        self.keycloak = keycloak

    async def list_users(self) -> list[dict]:
        return await self.keycloak.list_users()

    async def get_user(self, user_id: str) -> dict:
        return await self.keycloak.get_user(user_id)

    async def update_user_role(self, user_id: str, role: UserRole) -> dict:
        return await self.keycloak.update_user_role(user_id, role)


async def user_manager_dependency(
    keycloak: KeycloakManager = Depends(keycloak_manager_dependency),  # noqa: B008
) -> UserManager:
    return UserManager(keycloak)
