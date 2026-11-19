from collections.abc import Sequence

from nova.domain.shared.events import DomainEvent


class EventPublisher:
    async def publish(self, event: DomainEvent) -> None: ...

    async def publish_many(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
