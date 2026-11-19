import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from uuid import UUID

from redis.asyncio import Redis

from nova.application.ports.events import EventPublisher
from nova.domain.shared.events import DomainEvent

EVENT_CHANNEL_PREFIX = "nova:events"


def _default(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Unsupported type: {type(value)}")


def serialize_event(event: DomainEvent) -> str:
    payload = dict(asdict(event))
    payload["event_type"] = event.event_type
    payload["aggregate_id"] = str(event.aggregate_id)
    return json.dumps(payload, default=_default, separators=(",", ":"))


class RedisEventPublisher(EventPublisher):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(self, event: DomainEvent) -> None:
        message = serialize_event(event)
        user_id = getattr(event, "user_id", None)
        if user_id is None:
            return
        channels = [f"{EVENT_CHANNEL_PREFIX}:{user_id}", f"{EVENT_CHANNEL_PREFIX}:all"]
        for channel in channels:
            await self._redis.publish(channel, message)

    async def publish_many(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
