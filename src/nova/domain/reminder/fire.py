from dataclasses import dataclass
from datetime import datetime

from nova.domain.shared.ids import FireId, ReminderId, UserId


@dataclass(frozen=True, slots=True)
class ReminderFire:
    id: FireId
    reminder_id: ReminderId
    user_id: UserId
    fired_at: datetime
