from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from nova.domain.shared.errors import DomainError


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        raise NotImplementedError

    @property
    def aggregate_id(self) -> UUID:
        raise NotImplementedError


class AggregateRoot:
    __slots__ = ("_events",)

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def raise_event(self, event: DomainEvent) -> None:
        self._events.append(event)


class ConcurrencyConflict(DomainError):
    pass
