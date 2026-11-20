from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine

from nova.application.ports.events import EventPublisher
from nova.application.ports.push import PushNotifier
from nova.application.ports.security import Clock
from nova.application.reminder.use_cases import FireReminder
from nova.domain.shared.ids import as_uuid
from nova.infrastructure.config import Settings
from nova.infrastructure.persistence.database import UnitOfWorkFactory

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

FIRE_NAMESPACE = UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


class ReminderScheduler:
    def __init__(
        self,
        settings: Settings,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        publisher: EventPublisher,
        push: PushNotifier,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._publisher = publisher
        self._push = push
        sync_engine: Engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(engine=sync_engine)},
            timezone="UTC",
        )

    async def start(self) -> None:
        _bind(self)
        self.scheduler.add_job(
            "nova.infrastructure.scheduler.reminder_scheduler:reconcile_job",
            trigger="interval",
            seconds=30,
            id="nova-reconcile",
            replace_existing=True,
            misfire_grace_time=30,
        )
        self.scheduler.start()
        await self._reconcile()

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _reconcile(self) -> None:
        async with self._uow_factory() as uow:
            reminders = await uow.reminders.list_scheduled()
        desired: dict[str, tuple[UUID, UUID, object]] = {}
        for reminder in reminders:
            fire_id = uuid5(
                FIRE_NAMESPACE,
                f"{reminder.id}:{reminder.due_at.value.isoformat()}:{reminder.version}",
            )
            desired[f"fire-{fire_id}"] = (as_uuid(reminder.id), fire_id, reminder.due_at.value)
        existing = {job.id for job in self.scheduler.get_jobs() if job.id.startswith("fire-")}
        for job_id in existing - desired.keys():
            self.scheduler.remove_job(job_id)
        for job_id, (reminder_id, fire_id, due_at) in desired.items():
            if job_id in existing:
                continue
            self.scheduler.add_job(
                "nova.infrastructure.scheduler.reminder_scheduler:fire_job",
                trigger="date",
                run_date=due_at,
                args=[reminder_id, fire_id],
                id=job_id,
                misfire_grace_time=300,
                replace_existing=True,
                timezone="UTC",
            )

    async def _fire(self, reminder_id: UUID, fire_id: UUID) -> None:
        async with self._uow_factory() as uow:
            use_case = FireReminder(uow, self._clock, self._publisher, self._push)
            await use_case.execute(reminder_id, fire_id)


_current: ReminderScheduler | None = None


def _bind(scheduler: ReminderScheduler) -> None:
    global _current
    _current = scheduler


async def reconcile_job() -> None:
    if _current is not None:
        await _current._reconcile()


async def fire_job(reminder_id: UUID, fire_id: UUID) -> None:
    if _current is not None:
        await _current._fire(reminder_id, fire_id)
