from uuid import UUID

from nova.application.ports.uow import UnitOfWork
from nova.application.sync.dto import SyncChangeView, SyncResult
from nova.domain.shared.ids import ChangeId, UserId


class GetChanges:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, cursor: int, limit: int = 100) -> SyncResult:
        changes = await self._uow.changes.list_since(UserId(user_id), ChangeId(cursor), limit=limit)
        views = [
            SyncChangeView(
                id=int(change.id),
                aggregate_type=change.aggregate_type,
                aggregate_id=change.aggregate_id,
                version=change.version,
                payload=change.payload,
                occurred_at=change.occurred_at,
            )
            for change in changes
        ]
        next_cursor = int(views[-1].id) if views else cursor
        return SyncResult(changes=views, next_cursor=next_cursor)
