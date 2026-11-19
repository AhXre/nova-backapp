from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from nova.domain.reminder.reminder import ReminderOrigin, ReminderStatus


@dataclass(frozen=True, slots=True)
class CreateReminderCommand:
    user_id: UUID
    content: str
    due_at: datetime
    recurrence: str | None = None
    origin: ReminderOrigin = ReminderOrigin.MOBILE


@dataclass(frozen=True, slots=True)
class UpdateReminderCommand:
    user_id: UUID
    reminder_id: UUID
    content: str
    due_at: datetime
    recurrence: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class SnoozeReminderCommand:
    user_id: UUID
    reminder_id: UUID
    snooze_until: datetime
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class ReminderView:
    id: UUID
    user_id: UUID
    content: str
    due_at: datetime
    recurrence: str | None
    status: ReminderStatus
    origin: ReminderOrigin
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
