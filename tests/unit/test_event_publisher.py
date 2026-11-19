import json
from uuid import uuid4

import pytest
from tests.conftest import FakeRedis

from nova.domain.reminder.events import ReminderCreated
from nova.infrastructure.events.redis_event_bus import RedisEventPublisher


@pytest.mark.asyncio
async def test_publisher_sends_user_and_global_channels() -> None:
    redis = FakeRedis()
    publisher = RedisEventPublisher(redis)  # type: ignore[arg-type]
    user_id = uuid4()
    event = ReminderCreated(
        reminder_id=uuid4(),
        user_id=user_id,
    )
    await publisher.publish(event)
    assert [channel for channel, _ in redis.published] == [
        f"nova:events:{user_id}",
        "nova:events:all",
    ]
    payload = json.loads(redis.published[0][1])
    assert payload["event_type"] == "reminder.created"
    assert payload["occurred_at"] == event.occurred_at.isoformat()
