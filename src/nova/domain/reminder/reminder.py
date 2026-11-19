from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from nova.domain.reminder.events import (
    ReminderCreated,
    ReminderDeleted,
    ReminderFired,
    ReminderUpdated,
)
from nova.domain.reminder.value_objects import DueAt, RecurrenceRule, ReminderContent
from nova.domain.shared.errors import InvalidTransition, ValidationError
from nova.domain.shared.events import AggregateRoot
from nova.domain.shared.ids import FireId, ReminderId, UserId, as_uuid


class ReminderStatus(StrEnum):
    PENDING = "pending"
    FIRED = "fired"
    SNOOZED = "snoozed"
    DONE = "done"


class ReminderOrigin(StrEnum):
    DEVICE = "device"
    MOBILE = "mobile"
    DESKTOP = "desktop"


@dataclass(slots=True)
class Reminder(AggregateRoot):
    id: ReminderId
    user_id: UserId
    content: ReminderContent
    due_at: DueAt
    recurrence: RecurrenceRule
    status: ReminderStatus
    origin: ReminderOrigin
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        super().__init__()
        if self.version < 1:
            raise ValidationError("version must be >= 1")

    @classmethod
    def create(
        cls,
        reminder_id: ReminderId,
        user_id: UserId,
        content: ReminderContent,
        due_at: DueAt,
        recurrence: RecurrenceRule,
        origin: ReminderOrigin,
        now: datetime,
    ) -> "Reminder":
        reminder = cls(
            id=reminder_id,
            user_id=user_id,
            content=content,
            due_at=due_at,
            recurrence=recurrence,
            status=ReminderStatus.PENDING,
            origin=origin,
            version=1,
            created_at=now,
            updated_at=now,
        )
        reminder.raise_event(
            ReminderCreated(
                event_id=uuid4(),
                occurred_at=now,
                reminder_id=as_uuid(reminder_id),
                user_id=as_uuid(user_id),
            )
        )
        return reminder

    def assert_version(self, expected: int) -> None:
        if self.version != expected:
            raise InvalidTransition(f"version conflict: expected {expected}, found {self.version}")

    def update(
        self,
        content: ReminderContent,
        due_at: DueAt,
        recurrence: RecurrenceRule,
        now: datetime,
    ) -> None:
        if self.deleted_at is not None:
            raise InvalidTransition("cannot update a deleted reminder")
        if self.status in (ReminderStatus.FIRED, ReminderStatus.DONE):
            raise InvalidTransition(f"cannot update a {self.status} reminder")
        self.content = content
        self.due_at = due_at
        self.recurrence = recurrence
        self.version += 1
        self.updated_at = now
        self.raise_event(
            ReminderUpdated(
                event_id=uuid4(),
                occurred_at=now,
                reminder_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
                version=self.version,
            )
        )

    def mark_fired(self, fire_id: FireId, now: datetime) -> None:
        if self.deleted_at is not None:
            raise InvalidTransition("cannot fire a deleted reminder")
        if self.status not in (ReminderStatus.PENDING, ReminderStatus.SNOOZED):
            raise InvalidTransition(f"cannot fire a {self.status} reminder")
        self.status = ReminderStatus.FIRED
        self.version += 1
        self.updated_at = now
        self.raise_event(
            ReminderFired(
                event_id=uuid4(),
                occurred_at=now,
                reminder_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
                fire_id=as_uuid(fire_id),
                due_at=self.due_at.value,
            )
        )

    def snooze(self, until: DueAt, now: datetime) -> None:
        if self.status != ReminderStatus.FIRED:
            raise InvalidTransition("only fired reminders can be snoozed")
        if until.value <= now:
            raise ValidationError("snooze time must be in the future")
        self.status = ReminderStatus.SNOOZED
        self.due_at = until
        self.version += 1
        self.updated_at = now
        self.raise_event(
            ReminderUpdated(
                event_id=uuid4(),
                occurred_at=now,
                reminder_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
                version=self.version,
            )
        )

    def mark_done(self, now: datetime) -> None:
        if self.deleted_at is not None or self.status == ReminderStatus.DONE:
            raise InvalidTransition("reminder is already finished")
        self.status = ReminderStatus.DONE
        self.version += 1
        self.updated_at = now
        self.raise_event(
            ReminderUpdated(
                event_id=uuid4(),
                occurred_at=now,
                reminder_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
                version=self.version,
            )
        )

    def soft_delete(self, now: datetime) -> None:
        if self.deleted_at is not None:
            raise InvalidTransition("reminder already deleted")
        self.deleted_at = now
        self.version += 1
        self.updated_at = now
        self.raise_event(
            ReminderDeleted(
                event_id=uuid4(),
                occurred_at=now,
                reminder_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
                version=self.version,
            )
        )
