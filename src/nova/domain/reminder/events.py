from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from nova.domain.shared.events import DomainEvent


@dataclass(frozen=True, slots=True)
class ReminderCreated(DomainEvent):
    reminder_id: UUID
    user_id: UUID

    @property
    def event_type(self) -> str:
        return "reminder.created"

    @property
    def aggregate_id(self) -> UUID:
        return self.reminder_id


@dataclass(frozen=True, slots=True)
class ReminderUpdated(DomainEvent):
    reminder_id: UUID
    user_id: UUID
    version: int

    @property
    def event_type(self) -> str:
        return "reminder.updated"

    @property
    def aggregate_id(self) -> UUID:
        return self.reminder_id


@dataclass(frozen=True, slots=True)
class ReminderDeleted(DomainEvent):
    reminder_id: UUID
    user_id: UUID
    version: int

    @property
    def event_type(self) -> str:
        return "reminder.deleted"

    @property
    def aggregate_id(self) -> UUID:
        return self.reminder_id


@dataclass(frozen=True, slots=True)
class ReminderFired(DomainEvent):
    reminder_id: UUID
    user_id: UUID
    fire_id: UUID
    due_at: datetime

    @property
    def event_type(self) -> str:
        return "reminder.fired"

    @property
    def aggregate_id(self) -> UUID:
        return self.reminder_id
