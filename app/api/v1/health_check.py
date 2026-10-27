from typing import Any

from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.service import health
from app.utils.exceptions import UnAvailableService

router = APIRouter(prefix="/health", tags=["Health Check"])


@router.get("/live")
def liveness():
    try:
        return {"status": "ok"}
    except Exception as e:
        raise UnAvailableService(
            message=str(e),
            status_code=500,
            error_code="Code Unavailable",
            content={
                "status": "Service Unavailable at this time",
            },
        )


@router.get("/ready")
async def readiness() -> Any:
    result = await health.check_all()
    status_code = 200 if result["healthy"] else 503
    return JSONResponse(status_code=status_code, content=result)
