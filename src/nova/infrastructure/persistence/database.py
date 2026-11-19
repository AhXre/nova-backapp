from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from nova.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork

T = TypeVar("T")


class Database:
    def __init__(self, url: str, echo: bool = False) -> None:
        options: dict[str, object] = {"echo": echo, "pool_pre_ping": True}
        if url.startswith("sqlite"):
            options["poolclass"] = NullPool
        self.engine: AsyncEngine = create_async_engine(url, **options)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    def uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    async def dispose(self) -> None:
        await self.engine.dispose()


async def session_generator(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.session_factory() as session:
        yield session


UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]
