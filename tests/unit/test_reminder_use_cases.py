from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from tests.conftest import FakePush, FakeUnitOfWork

from nova.application.errors import NotFoundError
from nova.application.reminder.dto import CreateReminderCommand, UpdateReminderCommand
from nova.application.reminder.use_cases import (
    CreateReminder,
    DeleteReminder,
    FireReminder,
    GetReminder,
    ListReminders,
    UpdateReminder,
)
from nova.bootstrap import Container
from nova.domain.device.device import Device
from nova.domain.shared.ids import DeviceId, UserId


@pytest.mark.asyncio
async def test_reminder_lifecycle_and_sync_events(
    uow: FakeUnitOfWork,
    container: Container,
) -> None:
    user_id = uuid4()
    now = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
    create = CreateReminder(uow, container.clock, container.publisher)
    created = await create.execute(
        CreateReminderCommand(
            user_id=user_id, content="Llamar al dentista", due_at=now + timedelta(hours=1)
        )
    )
    assert created.version == 1
    assert await ListReminders(uow).execute(user_id) == [created]

    updated = await UpdateReminder(uow, container.clock, container.publisher).execute(
        UpdateReminderCommand(
            user_id=user_id,
            reminder_id=created.id,
            content="Llamar al dentista",
            due_at=now + timedelta(hours=2),
            expected_version=1,
        )
    )
    assert updated.version == 2

    await DeleteReminder(uow, container.clock, container.publisher).execute(user_id, created.id)
    with pytest.raises(NotFoundError):
        await GetReminder(uow).execute(user_id, created.id)
    assert len(uow.changes.items) == 3
    assert [change.aggregate_type for change in uow.changes.items] == ["reminder"] * 3


@pytest.mark.asyncio
async def test_fire_is_deduplicated_and_pushes_once(
    uow: FakeUnitOfWork,
    container: Container,
    push: FakePush,
) -> None:
    user_id = uuid4()
    device_id = uuid4()

    device = Device.pair(
        DeviceId(device_id),
        UserId(user_id),
        "Nova Pi",
        container.clock.now(),
    )
    device.update_push_token("fcm-token")
    await uow.devices.add(device)

    created = await CreateReminder(uow, container.clock, container.publisher).execute(
        CreateReminderCommand(
            user_id=user_id, content="Tomar medicina", due_at=container.clock.now()
        )
    )
    fire_id = uuid4()
    fire = FireReminder(uow, container.clock, container.publisher, push)
    await fire.execute(created.id, fire_id)
    await fire.execute(created.id, fire_id)
    assert len(uow.fires.items) == 1
    assert len(push.calls) == 1
    assert push.calls[0][0] == ["fcm-token"]
