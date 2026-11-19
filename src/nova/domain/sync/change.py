from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from nova.domain.shared.ids import ChangeId, UserId


@dataclass(frozen=True, slots=True)
class Change:
    id: ChangeId
    user_id: UserId
    aggregate_type: str
    aggregate_id: UUID
    version: int
    payload: dict[str, object]
    occurred_at: datetime
