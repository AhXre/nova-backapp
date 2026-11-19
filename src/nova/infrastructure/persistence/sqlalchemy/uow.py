from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nova.application.ports.uow import UnitOfWork
from nova.infrastructure.persistence.sqlalchemy.repositories import (
    SqlAlchemyChangeRepository,
    SqlAlchemyDeviceRepository,
    SqlAlchemyFireRepository,
    SqlAlchemyPairingCodeRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyReminderRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        self.refresh_tokens = SqlAlchemyRefreshTokenRepository(self.session)
        self.pairing_codes = SqlAlchemyPairingCodeRepository(self.session)
        self.devices = SqlAlchemyDeviceRepository(self.session)
        self.reminders = SqlAlchemyReminderRepository(self.session)
        self.fires = SqlAlchemyFireRepository(self.session)
        self.changes = SqlAlchemyChangeRepository(self.session)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()
        self._session = None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[UnitOfWork]:
        async with self as uow:
            try:
                yield uow
                await uow.commit()
            except Exception:
                await uow.rollback()
                raise


def uow_factory(session_factory: async_sessionmaker[AsyncSession]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)
