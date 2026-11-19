import asyncio
import signal

from nova.bootstrap import build_container
from nova.infrastructure.config import get_settings
from nova.infrastructure.logging import configure_logging
from nova.infrastructure.scheduler.reminder_scheduler import ReminderScheduler


async def main() -> None:
    settings = get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")
    container = build_container(settings)
    scheduler = ReminderScheduler(
        settings,
        container.uow,
        container.clock,
        container.publisher,
        container.push,
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await scheduler.start()
    try:
        await stop.wait()
    finally:
        await scheduler.shutdown()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
