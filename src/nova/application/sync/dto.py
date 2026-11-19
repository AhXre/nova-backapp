from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SyncChangeView:
    id: int
    aggregate_type: str
    aggregate_id: UUID
    version: int
    payload: dict[str, object]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class SyncResult:
    changes: list[SyncChangeView]
    next_cursor: int
