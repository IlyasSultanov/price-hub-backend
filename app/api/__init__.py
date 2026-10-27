__all__ = (
    "feeds_router",
    "health_router",
    "mapping_profiles_router",
    "supplier_router",
    "users_router",
)

from .v1.feeds import router as feeds_router
from .v1.health_check import router as health_router
from .v1.mapping_profiles import router as mapping_profiles_router
from .v1.suppliers import router as supplier_router
from .v1.users import router as users_router
