import asyncio
import logging
import time
from urllib.parse import quote

import httpx
from fastapi import status

from ...core import settings
from ...utils import _MAX_ATTEMPTS, _STATUS_CODE, UserRole
from ...utils.exceptions import KeycloakAdminError
from .utils import get_admin_realm_url

logger = logging.getLogger(__name__)


def _admin_error(message: str, status_code: int, error_code: str) -> KeycloakAdminError:
    return KeycloakAdminError(
        message=message, status_code=status_code, error_code=error_code, content={}
    )


class KeycloakManager:
    """Thin client over the Keycloak Admin REST API (user listing + realm
    role assignment). Not used for request-time auth — see
    `app.core.security` for the JWT/JWKS verification that actually gates
    endpoints; this is only for the admin-facing user management screens."""

    def __init__(self) -> None:
        self._admin_token: str | None = None
        self._token_expires_at = 0.0
        self._lock = asyncio.Lock()

    async def _get_admin_token(
        self, client: httpx.AsyncClient, *, force_refresh: bool = False
    ) -> str:
        if (
            not force_refresh
            and self._admin_token
            and time.monotonic() < self._token_expires_at
        ):
            return self._admin_token

        async with self._lock:
            if (
                not force_refresh
                and self._admin_token
                and time.monotonic() < self._token_expires_at
            ):
                return self._admin_token

            if (
                not settings.keycloak_config.client_id
                or not settings.keycloak_config.client_secret
            ):
                raise _admin_error(
                    "Keycloak client ID or secret is not configured.",
                    status.HTTP_502_BAD_GATEWAY,
                    "INVALID_CLIENT_CONFIG",
                )

            token_url = (
                f"{settings.keycloak_config.server_url.rstrip('/')}/realms/"
                f"{quote(settings.keycloak_config.realm, safe='')}/protocol/openid-connect/token"
            )
            try:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.keycloak_config.client_id,
                        "client_secret": settings.keycloak_config.client_secret,
                    },
                    timeout=10.0,
                )
            except httpx.RequestError as exc:
                raise _admin_error(
                    f"Error connecting to Keycloak: {exc}",
                    status.HTTP_502_BAD_GATEWAY,
                    "KEYCLOAK_CONNECTION_ERROR",
                ) from exc

            if response.status_code in _STATUS_CODE:
                raise _admin_error(
                    f"Keycloak service unavailable. Status code: {response.status_code}",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "KEYCLOAK_SERVICE_UNAVAILABLE",
                )
            if response.is_error:
                raise _admin_error(
                    f"Failed to obtain admin token from Keycloak. "
                    f"Status code: {response.status_code}, Response: {response.text}",
                    status.HTTP_502_BAD_GATEWAY,
                    "KEYCLOAK_TOKEN_ERROR",
                )

            token_payload = response.json()
            token = token_payload.get("access_token")
            if not token:
                raise _admin_error(
                    "Failed to obtain admin token from Keycloak.",
                    status.HTTP_502_BAD_GATEWAY,
                    "KEYCLOAK_TOKEN_ERROR",
                )

            self._admin_token = token
            expires_in = int(token_payload.get("expires_in", 60))
            self._token_expires_at = time.monotonic() + max(expires_in - 10, 0)
            return token

    async def _send_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        json: object = None,
        params: dict | None = None,
    ) -> httpx.Response:
        url = f"{get_admin_realm_url()}/{path.lstrip('/')}"
        force_refresh = False

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            token = await self._get_admin_token(client, force_refresh=force_refresh)
            try:
                response = await client.request(
                    method,
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json=json,
                    params=params,
                    timeout=10.0,
                )
            except httpx.RequestError as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise _admin_error(
                        f"Keycloak request failed after {attempt} attempts: {exc}",
                        status.HTTP_502_BAD_GATEWAY,
                        "KEYCLOAK_REQUEST_ERROR",
                    ) from exc
                await asyncio.sleep(1)
                continue

            if response.status_code == 401 and not force_refresh:
                self._admin_token = None
                self._token_expires_at = 0.0
                force_refresh = True
                continue
            if response.status_code == 404:
                return response
            if response.status_code in _STATUS_CODE:
                if attempt == _MAX_ATTEMPTS:
                    raise _admin_error(
                        f"Keycloak service unavailable after {attempt} attempts. "
                        f"Status code: {response.status_code}",
                        status.HTTP_503_SERVICE_UNAVAILABLE,
                        "KEYCLOAK_SERVICE_UNAVAILABLE",
                    )
                await asyncio.sleep(1)
                continue
            if response.is_error:
                raise _admin_error(
                    f"Keycloak request failed. Status code: {response.status_code}, "
                    f"Response: {response.text}",
                    status.HTTP_502_BAD_GATEWAY,
                    "KEYCLOAK_REQUEST_ERROR",
                )
            return response

        raise _admin_error(
            "Keycloak request failed after exhausting all retries.",
            status.HTTP_502_BAD_GATEWAY,
            "KEYCLOAK_REQUEST_ERROR",
        )

    async def _get_role_mappings(
        self, client: httpx.AsyncClient, user_id: str
    ) -> list[dict]:
        response = await self._send_request(
            client, "GET", f"users/{quote(user_id, safe='')}/role-mappings/realm"
        )
        return response.json()

    @staticmethod
    def _user_out(user: dict, role_names: set[str]) -> dict:
        roles = [role for role in UserRole if role.value in role_names]
        return {
            "id": user["id"],
            "username": user.get("username", ""),
            "email": user.get("email"),
            "first_name": user.get("firstName"),
            "last_name": user.get("lastName"),
            "roles": roles,
            "is_active": user.get("enabled", True),
        }

    async def _get_user(self, client: httpx.AsyncClient, user_id: str) -> dict:
        response = await self._send_request(
            client, "GET", f"users/{quote(user_id, safe='')}"
        )
        if response.status_code == 404:
            raise _admin_error(
                f"User {user_id} was not found in Keycloak",
                status.HTTP_404_NOT_FOUND,
                "KEYCLOAK_USER_NOT_FOUND",
            )
        return response.json()

    async def _user_with_roles(self, client: httpx.AsyncClient, user: dict) -> dict:
        role_mappings = await self._get_role_mappings(client, user["id"])
        role_names = {role["name"] for role in role_mappings}
        return self._user_out(user, role_names)

    async def _get_realm_role(self, client: httpx.AsyncClient, role: UserRole) -> dict:
        response = await self._send_request(
            client, "GET", f"roles/{quote(role.value, safe='')}"
        )
        if response.status_code == 404:
            raise _admin_error(
                f"Realm role {role.value!r} does not exist in Keycloak "
                "(it should be provisioned via the realm import)",
                status.HTTP_502_BAD_GATEWAY,
                "KEYCLOAK_ROLE_NOT_FOUND",
            )
        return response.json()

    async def list_users(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await self._send_request(
                client, "GET", "users", params={"max": 1000}
            )
            users = response.json()
            return [await self._user_with_roles(client, user) for user in users]

    async def get_user(self, user_id: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            user = await self._get_user(client, user_id)
            return await self._user_with_roles(client, user)

    async def update_user_role(self, user_id: str, role: UserRole) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            await self._get_user(
                client, user_id
            )  # 404s early if the user doesn't exist
            mappings = await self._get_role_mappings(client, user_id)
            app_role_names = {r.value for r in UserRole}
            roles_to_remove = [
                mapping
                for mapping in mappings
                if mapping["name"] in app_role_names and mapping["name"] != role.value
            ]
            if roles_to_remove:
                await self._send_request(
                    client,
                    "DELETE",
                    f"users/{quote(user_id, safe='')}/role-mappings/realm",
                    json=roles_to_remove,
                )

            if not any(mapping["name"] == role.value for mapping in mappings):
                realm_role = await self._get_realm_role(client, role)
                await self._send_request(
                    client,
                    "POST",
                    f"users/{quote(user_id, safe='')}/role-mappings/realm",
                    json=[realm_role],
                )

            return await self._user_with_roles(
                client, await self._get_user(client, user_id)
            )


keycloak_manager = KeycloakManager()


async def keycloak_manager_dependency() -> KeycloakManager:
    return keycloak_manager
