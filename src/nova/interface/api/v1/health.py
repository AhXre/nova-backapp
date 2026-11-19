from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from nova.bootstrap import Container
from nova.interface.api.v1.deps import get_container
from nova.interface.api.v1.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    return HealthResponse(status="ok", service=container.settings.app_name)


@router.get("/ready", response_model=HealthResponse)
async def ready(container: Container = Depends(get_container)) -> HealthResponse:
    try:
        async with container.database.session_factory() as session:
            await session.execute(text("SELECT 1"))
        await container.redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="dependency unavailable"
        ) from exc
    return HealthResponse(status="ready", service=container.settings.app_name)
