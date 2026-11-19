from collections.abc import Sequence
from dataclasses import asdict

from nova.application.ports.uow import UnitOfWork
from nova.domain.shared.events import DomainEvent


def event_payload(event: DomainEvent) -> dict[str, object]:
    payload: dict[str, object] = dict(asdict(event))
    payload["event_type"] = event.event_type
    payload["aggregate_id"] = str(event.aggregate_id)
    return payload


async def record_events(uow: UnitOfWork, events: Sequence[DomainEvent]) -> None:
    for event in events:
        await uow.changes.append(event, event_payload(event))
