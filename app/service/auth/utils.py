from urllib.parse import quote

from ...core import settings


def get_admin_realm_url() -> str:
    base_url = settings.keycloak_config.server_url.rstrip("/")
    realm = quote(settings.keycloak_config.realm, safe="")
    return f"{base_url}/admin/realms/{realm}"
