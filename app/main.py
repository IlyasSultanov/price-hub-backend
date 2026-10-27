from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    feeds_router,
    health_router,
    mapping_profiles_router,
    supplier_router,
    users_router,
)
from app.aws import get_s3_client
from app.core import settings
from app.middelwere.loggers import LoggingMiddleware
from app.workers import start_broker, stop_broker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:

    await start_broker()
    stack = AsyncExitStack()

    app.state.s3 = await stack.enter_async_context(get_s3_client())
    yield
    await stop_broker()
    await stack.aclose()


app = FastAPI(
    lifespan=lifespan,
)

app.add_middleware(
    LoggingMiddleware,
)

# Added last = runs outermost, so preflight is handled before anything else.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(supplier_router, prefix="/api/v1")
app.include_router(feeds_router, prefix="/api/v1")
app.include_router(mapping_profiles_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
