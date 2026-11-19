from collections.abc import Sequence
from datetime import datetime

from nova.domain.device.device import Device
from nova.domain.identity.pairing_code import PairingCode
from nova.domain.identity.refresh_token import RefreshToken
from nova.domain.identity.user import User
from nova.domain.reminder.fire import ReminderFire
from nova.domain.reminder.reminder import Reminder
from nova.domain.shared.events import DomainEvent
from nova.domain.shared.ids import (
    ChangeId,
    DeviceId,
    FireId,
    RefreshTokenId,
    ReminderId,
    UserId,
)
from nova.domain.sync.change import Change


class UserRepository:
    async def add(self, user: User) -> None: ...

    async def get(self, user_id: UserId) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class RefreshTokenRepository:
    async def add(self, token: RefreshToken) -> None: ...

    async def get(self, token_id: RefreshTokenId) -> RefreshToken | None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def save(self, token: RefreshToken) -> None: ...


class PairingCodeRepository:
    async def add(self, code: PairingCode) -> None: ...

    async def get_by_hash(self, code_hash: str) -> PairingCode | None: ...

    async def save(self, code: PairingCode) -> None: ...


class DeviceRepository:
    async def add(self, device: Device) -> None: ...

    async def get(self, device_id: DeviceId) -> Device | None: ...

    async def list_for_user(self, user_id: UserId) -> Sequence[Device]: ...

    async def save(self, device: Device) -> None: ...

    async def list_push_tokens(self, user_id: UserId) -> Sequence[str]: ...


class ReminderRepository:
    async def add(self, reminder: Reminder) -> None: ...

    async def get(self, user_id: UserId, reminder_id: ReminderId) -> Reminder | None: ...

    async def get_by_id(self, reminder_id: ReminderId) -> Reminder | None: ...

    async def list_for_user(
        self,
        user_id: UserId,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Reminder]: ...

    async def list_due(self, now: datetime, limit: int = 100) -> Sequence[Reminder]: ...

    async def list_scheduled(self, limit: int = 1000) -> Sequence[Reminder]: ...

    async def save(self, reminder: Reminder) -> None: ...


class FireRepository:
    async def add(self, fire: ReminderFire) -> bool: ...

    async def has(self, fire_id: FireId) -> bool: ...


class ChangeRepository:
    async def append(self, event: DomainEvent, payload: dict[str, object]) -> Change: ...

    async def list_since(
        self,
        user_id: UserId,
        cursor: ChangeId,
        limit: int = 100,
    ) -> Sequence[Change]: ...
