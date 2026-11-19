from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from nova.domain.reminder.events import ReminderCreated, ReminderFired
from nova.domain.reminder.reminder import Reminder, ReminderOrigin, ReminderStatus
from nova.domain.reminder.value_objects import DueAt, RecurrenceRule, ReminderContent
from nova.domain.shared.errors import InvalidTransition, ValidationError
from nova.domain.shared.ids import FireId, UserId, new_fire_id, new_reminder_id


def make_reminder(now: datetime) -> Reminder:
    return Reminder.create(
        reminder_id=new_reminder_id(),
        user_id=UserId(uuid4()),
        content=ReminderContent("Llamar al dentista"),
        due_at=DueAt(now + timedelta(hours=1)),
        recurrence=RecurrenceRule(),
        origin=ReminderOrigin.MOBILE,
        now=now,
    )


def test_create_emits_domain_event(now: datetime) -> None:
    reminder = make_reminder(now)
    events = reminder.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], ReminderCreated)
    assert events[0].event_type == "reminder.created"
    assert reminder.pull_events() == []


def test_content_and_timezone_invariants(now: datetime) -> None:
    with pytest.raises(ValidationError):
        ReminderContent("   ")
    with pytest.raises(ValidationError):
        DueAt(datetime(2026, 1, 1))


def test_update_increments_version(now: datetime) -> None:
    reminder = make_reminder(now)
    reminder.pull_events()
    reminder.update(
        ReminderContent("Llamar al dentista"),
        DueAt(now + timedelta(hours=2)),
        RecurrenceRule(),
        now,
    )
    assert reminder.version == 2
    assert reminder.due_at.value == now + timedelta(hours=2)


def test_fire_is_idempotent_by_state(now: datetime) -> None:
    reminder = make_reminder(now)
    reminder.pull_events()
    fire_id = new_fire_id()
    reminder.mark_fired(fire_id, now)
    assert isinstance(reminder.pull_events()[0], ReminderFired)
    with pytest.raises(InvalidTransition):
        reminder.mark_fired(FireId(uuid4()), now)


def test_delete_is_a_tombstone(now: datetime) -> None:
    reminder = make_reminder(now)
    reminder.pull_events()
    reminder.soft_delete(now)
    assert reminder.deleted_at == now
    assert reminder.status == ReminderStatus.PENDING
    with pytest.raises(InvalidTransition):
        reminder.soft_delete(now)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
