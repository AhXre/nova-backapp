from collections.abc import Sequence
from uuid import UUID

from nova.application.errors import NotFoundError
from nova.application.events import record_events
from nova.application.ports.events import EventPublisher
from nova.application.ports.push import PushNotifier
from nova.application.ports.security import Clock
from nova.application.ports.uow import UnitOfWork
from nova.application.reminder.dto import (
    CreateReminderCommand,
    ReminderView,
    SnoozeReminderCommand,
    UpdateReminderCommand,
)
from nova.domain.reminder.fire import ReminderFire
from nova.domain.reminder.reminder import Reminder
from nova.domain.reminder.value_objects import DueAt, RecurrenceRule, ReminderContent
from nova.domain.shared.ids import FireId, ReminderId, UserId, as_uuid, new_reminder_id


def to_view(reminder: Reminder) -> ReminderView:
    return ReminderView(
        id=as_uuid(reminder.id),
        user_id=as_uuid(reminder.user_id),
        content=reminder.content.value,
        due_at=reminder.due_at.value,
        recurrence=reminder.recurrence.value,
        status=reminder.status,
        origin=reminder.origin,
        version=reminder.version,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        deleted_at=reminder.deleted_at,
    )


async def _publish(uow: UnitOfWork, publisher: EventPublisher, reminder: Reminder) -> None:
    events = reminder.pull_events()
    await record_events(uow, events)
    await uow.commit()
    await publisher.publish_many(events)


class CreateReminder:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(self, command: CreateReminderCommand) -> ReminderView:
        now = self._clock.now()
        reminder = Reminder.create(
            reminder_id=new_reminder_id(),
            user_id=UserId(command.user_id),
            content=ReminderContent(command.content),
            due_at=DueAt(command.due_at),
            recurrence=RecurrenceRule(command.recurrence),
            origin=command.origin,
            now=now,
        )
        await self._uow.reminders.add(reminder)
        await _publish(self._uow, self._publisher, reminder)
        return to_view(reminder)


class GetReminder:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, reminder_id: UUID) -> ReminderView:
        reminder = await self._uow.reminders.get(UserId(user_id), ReminderId(reminder_id))
        if reminder is None or reminder.deleted_at is not None:
            raise NotFoundError("reminder not found")
        return to_view(reminder)


class ListReminders:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ReminderView]:
        reminders = await self._uow.reminders.list_for_user(
            UserId(user_id), limit=limit, offset=offset
        )
        return [to_view(reminder) for reminder in reminders]


class UpdateReminder:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(self, command: UpdateReminderCommand) -> ReminderView:
        reminder = await self._uow.reminders.get(
            UserId(command.user_id), ReminderId(command.reminder_id)
        )
        if reminder is None or reminder.deleted_at is not None:
            raise NotFoundError("reminder not found")
        if command.expected_version is not None:
            reminder.assert_version(command.expected_version)
        reminder.update(
            content=ReminderContent(command.content),
            due_at=DueAt(command.due_at),
            recurrence=RecurrenceRule(command.recurrence),
            now=self._clock.now(),
        )
        await self._uow.reminders.save(reminder)
        await _publish(self._uow, self._publisher, reminder)
        return to_view(reminder)


class DeleteReminder:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(self, user_id: UUID, reminder_id: UUID) -> None:
        reminder = await self._uow.reminders.get(UserId(user_id), ReminderId(reminder_id))
        if reminder is None or reminder.deleted_at is not None:
            raise NotFoundError("reminder not found")
        reminder.soft_delete(self._clock.now())
        await self._uow.reminders.save(reminder)
        await _publish(self._uow, self._publisher, reminder)


class SnoozeReminder:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(self, command: SnoozeReminderCommand) -> ReminderView:
        reminder = await self._uow.reminders.get(
            UserId(command.user_id), ReminderId(command.reminder_id)
        )
        if reminder is None or reminder.deleted_at is not None:
            raise NotFoundError("reminder not found")
        if command.expected_version is not None:
            reminder.assert_version(command.expected_version)
        reminder.snooze(DueAt(command.snooze_until), self._clock.now())
        await self._uow.reminders.save(reminder)
        await _publish(self._uow, self._publisher, reminder)
        return to_view(reminder)


class MarkReminderDone:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(self, user_id: UUID, reminder_id: UUID) -> ReminderView:
        reminder = await self._uow.reminders.get(UserId(user_id), ReminderId(reminder_id))
        if reminder is None or reminder.deleted_at is not None:
            raise NotFoundError("reminder not found")
        reminder.mark_done(self._clock.now())
        await self._uow.reminders.save(reminder)
        await _publish(self._uow, self._publisher, reminder)
        return to_view(reminder)


class FireReminder:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        publisher: EventPublisher,
        push: PushNotifier,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher
        self._push = push

    async def execute(self, reminder_id: UUID, fire_id: UUID) -> None:
        fire = FireId(fire_id)
        if await self._uow.fires.has(fire):
            return
        reminder = await self._uow.reminders.get_by_id(ReminderId(reminder_id))
        if reminder is None or reminder.deleted_at is not None:
            return
        now = self._clock.now()
        reminder.mark_fired(fire, now)
        added = await self._uow.fires.add(
            ReminderFire(id=fire, reminder_id=reminder.id, user_id=reminder.user_id, fired_at=now)
        )
        if not added:
            await self._uow.rollback()
            return
        tokens = await self._uow.devices.list_push_tokens(reminder.user_id)
        await _publish(self._uow, self._publisher, reminder)
        if tokens:
            await self._push.send(
                tokens,
                title="Recordatorio",
                body=reminder.content.value,
                data={
                    "event_type": "reminder.fired",
                    "reminder_id": str(reminder.id),
                    "fire_id": str(fire),
                },
            )
