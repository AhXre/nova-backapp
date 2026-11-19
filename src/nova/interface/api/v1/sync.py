from uuid import UUID

from fastapi import APIRouter, Depends, Query

from nova.application.ports.uow import UnitOfWork
from nova.bootstrap import Container
from nova.interface.api.v1.deps import current_principal, get_container, get_uow
from nova.interface.api.v1.schemas import SyncResponse

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("", response_model=SyncResponse)
async def get_changes(
    since: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> SyncResponse:
    result = await container.sync(uow).get_changes.execute(user_id, since, limit)
    return SyncResponse.model_validate(result)
