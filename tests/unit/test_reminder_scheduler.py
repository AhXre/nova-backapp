from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from tests.conftest import FakePublisher, FakePush, FixedClock

from nova.infrastructure.config import Settings
from nova.infrastructure.scheduler.reminder_scheduler import ReminderScheduler

if TYPE_CHECKING:
    from nova.infrastructure.persistence.database import UnitOfWorkFactory


def test_jobs_use_serializable_function_references(
    clock: FixedClock,
    publisher: FakePublisher,
    push: FakePush,
) -> None:
    uow_factory = cast("UnitOfWorkFactory", lambda: None)
    scheduler = ReminderScheduler(
        Settings(database_url_sync="sqlite://"), uow_factory, clock, publisher, push
    )
    run_date = datetime.now(UTC) + timedelta(minutes=1)
    reminder_id, fire_id = uuid4(), uuid4()

    reconcile = scheduler.scheduler.add_job(
        "nova.infrastructure.scheduler.reminder_scheduler:reconcile_job",
        trigger="date",
        run_date=run_date,
    )
    fire = scheduler.scheduler.add_job(
        "nova.infrastructure.scheduler.reminder_scheduler:fire_job",
        trigger="date",
        run_date=run_date,
        args=[reminder_id, fire_id],
    )

    assert reconcile.func_ref == "nova.infrastructure.scheduler.reminder_scheduler:reconcile_job"
    assert reconcile.args == ()
    assert fire.func_ref == "nova.infrastructure.scheduler.reminder_scheduler:fire_job"
    assert fire.args == (reminder_id, fire_id)
