from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from nova.application.ports.repositories import (
    ChangeRepository,
    DeviceRepository,
    FireRepository,
    PairingCodeRepository,
    RefreshTokenRepository,
    ReminderRepository,
    UserRepository,
)


class UnitOfWork:
    users: UserRepository
    refresh_tokens: RefreshTokenRepository
    pairing_codes: PairingCodeRepository
    devices: DeviceRepository
    reminders: ReminderRepository
    fires: FireRepository
    changes: ChangeRepository

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["UnitOfWork"]:
        try:
            yield self
            await self.commit()
        except Exception:
            await self.rollback()
            raise
