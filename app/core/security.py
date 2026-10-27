import asyncio
import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from ..utils import UserRole
from .config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=True)

# Fetched lazily (on first protected request, not at import/startup) so the
# app can boot even if Keycloak is briefly unreachable; cached in-process for
# `lifespan` seconds afterwards.
_jwks_client = PyJWKClient(
    f"{settings.keycloak_config.issuer_url}/protocol/openid-connect/certs",
    lifespan=300,
)


@dataclass(frozen=True)
class Principal:
    subject: str
    username: str | None
    email: str | None
    roles: frozenset[UserRole]
    supplier_id: uuid.UUID | None

    def has_role(self, *roles: UserRole) -> bool:
        return bool(self.roles.intersection(roles))

    @property
    def is_admin(self) -> bool:
        return self.has_role(UserRole.CATALOG_ADMIN, UserRole.SYSTEM_ADMIN)


def _parse_supplier_id(raw: object) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


async def _decode_token(token: str) -> dict:
    try:
        # get_signing_key_from_jwt does a blocking HTTP call on a JWKS cache
        # miss; push it to a thread so it never stalls the event loop.
        signing_key = await asyncio.to_thread(
            _jwks_client.get_signing_key_from_jwt, token
        )
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            # iss/aud deliberately unchecked: a browser-issued token's `iss`
            # is the host-facing Keycloak URL (http://localhost:8080/...),
            # while this container reaches Keycloak over the docker network
            # (http://keycloak:8080/...) for the JWKS fetch above — the two
            # legitimately differ, so enforcing `issuer=` here would reject
            # every real token. Signature/exp/nbf/iat are still verified.
            options={"verify_aud": False, "verify_iss": False},
        )
    except jwt.PyJWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),  # noqa: B008
) -> Principal:
    claims = await _decode_token(credentials.credentials)

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token is missing the subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    realm_roles = set(claims.get("realm_access", {}).get("roles", []))
    roles = frozenset(role for role in UserRole if role.value in realm_roles)

    return Principal(
        subject=subject,
        username=claims.get("preferred_username"),
        email=claims.get("email"),
        roles=roles,
        supplier_id=_parse_supplier_id(claims.get("supplier_id")),
    )


def require_roles(*roles: UserRole):
    """FastAPI dependency factory: 403s unless the principal has one of `roles`."""

    async def _dependency(
        principal: Principal = Depends(get_current_principal),  # noqa: B008
    ) -> Principal:
        if not principal.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient role for this action",
            )
        return principal

    return _dependency


def ensure_supplier_access(principal: Principal, supplier_id: uuid.UUID) -> None:
    """SEC-2: a supplier_manager may only touch their own supplier's resources.

    Called from the service layer (not just the router) so ownership holds
    even if a future caller skips the router-level dependency.
    """
    if principal.is_admin:
        return
    if (
        UserRole.SUPPLIER_MANAGER in principal.roles
        and principal.supplier_id == supplier_id
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="you do not have access to this supplier's resources",
    )
