from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from nova.application.ports.events import EventPublisher
from nova.application.ports.push import PushNotifier
from nova.application.ports.rate_limit import RateLimiter
from nova.application.ports.security import Clock
from nova.bootstrap import Container
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
    as_uuid,
)
from nova.domain.sync.change import Change
from nova.infrastructure.config import Settings
from nova.infrastructure.security.jwt_service import JwtTokenService
from nova.infrastructure.security.password_hasher import Argon2PasswordHasher

if TYPE_CHECKING:
    from uuid import UUID


class FixedClock(Clock):
    def __init__(self, now: datetime | None = None) -> None:
        self.now_value = now or datetime.now(UTC).replace(microsecond=0)

    def now(self) -> datetime:
        return self.now_value

    def advance(self, seconds: int) -> None:
        self.now_value += timedelta(seconds=seconds)


class FakePublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


class FakePush(PushNotifier):
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str, str, dict[str, str] | None]] = []

    async def send(
        self,
        tokens: Sequence[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> list[str]:
        self.calls.append((list(tokens), title, body, data))
        return []


class FakeLimiter(RateLimiter):
    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        return True


class FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


class FakeDatabase:
    async def dispose(self) -> None:
        return None


class FakeUserRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self.items[as_uuid(user.id)] = user

    async def get(self, user_id: UserId) -> User | None:
        return self.items.get(as_uuid(user_id))

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.items.values() if user.email == email), None)


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, RefreshToken] = {}

    async def add(self, token: RefreshToken) -> None:
        self.items[as_uuid(token.id)] = token

    async def get(self, token_id: RefreshTokenId) -> RefreshToken | None:
        return self.items.get(as_uuid(token_id))

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next(
            (token for token in self.items.values() if token.token_hash == token_hash), None
        )

    async def save(self, token: RefreshToken) -> None:
        self.items[as_uuid(token.id)] = token


class FakePairingCodeRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, PairingCode] = {}

    async def add(self, code: PairingCode) -> None:
        self.items[as_uuid(code.id)] = code

    async def get_by_hash(self, code_hash: str) -> PairingCode | None:
        return next((code for code in self.items.values() if code.code_hash == code_hash), None)

    async def save(self, code: PairingCode) -> None:
        self.items[as_uuid(code.id)] = code


class FakeDeviceRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Device] = {}

    async def add(self, device: Device) -> None:
        self.items[as_uuid(device.id)] = device

    async def get(self, device_id: DeviceId) -> Device | None:
        return self.items.get(as_uuid(device_id))

    async def list_for_user(self, user_id: UserId) -> list[Device]:
        return [device for device in self.items.values() if device.user_id == user_id]

    async def save(self, device: Device) -> None:
        self.items[as_uuid(device.id)] = device

    async def list_push_tokens(self, user_id: UserId) -> list[str]:
        return [
            device.fcm_token
            for device in self.items.values()
            if device.user_id == user_id and device.fcm_token and device.revoked_at is None
        ]


class FakeReminderRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Reminder] = {}

    async def add(self, reminder: Reminder) -> None:
        self.items[as_uuid(reminder.id)] = reminder

    async def get(self, user_id: UserId, reminder_id: ReminderId) -> Reminder | None:
        reminder = self.items.get(as_uuid(reminder_id))
        return reminder if reminder and reminder.user_id == user_id else None

    async def get_by_id(self, reminder_id: ReminderId) -> Reminder | None:
        return self.items.get(as_uuid(reminder_id))

    async def list_for_user(
        self,
        user_id: UserId,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Reminder]:
        reminders = [
            reminder
            for reminder in self.items.values()
            if reminder.user_id == user_id and (include_deleted or reminder.deleted_at is None)
        ]
        return reminders[offset : offset + limit]

    async def list_due(self, now: datetime, limit: int = 100) -> list[Reminder]:
        return list(self.items.values())[:limit]

    async def list_scheduled(self, limit: int = 1000) -> list[Reminder]:
        return list(self.items.values())[:limit]

    async def save(self, reminder: Reminder) -> None:
        self.items[as_uuid(reminder.id)] = reminder


class FakeFireRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ReminderFire] = {}

    async def add(self, fire: ReminderFire) -> bool:
        if await self.has(fire.id):
            return False
        self.items[as_uuid(fire.id)] = fire
        return True

    async def has(self, fire_id: FireId) -> bool:
        return as_uuid(fire_id) in self.items


class FakeChangeRepository:
    def __init__(self) -> None:
        self.items: list[Change] = []
        self._next_id = 1

    async def append(self, event: DomainEvent, payload: dict[str, object]) -> Change:
        change = Change(
            id=ChangeId(self._next_id),
            user_id=UserId(as_uuid(str(event.user_id))),
            aggregate_type=event.event_type.split(".", 1)[0],
            aggregate_id=event.aggregate_id,
            version=int(payload.get("version", 1)),
            payload=payload,
            occurred_at=event.occurred_at,
        )
        self._next_id += 1
        self.items.append(change)
        return change

    async def list_since(
        self,
        user_id: UserId,
        cursor: ChangeId,
        limit: int = 100,
    ) -> list[Change]:
        return [
            change for change in self.items if change.user_id == user_id and change.id > cursor
        ][:limit]


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.users = FakeUserRepository()
        self.refresh_tokens = FakeRefreshTokenRepository()
        self.pairing_codes = FakePairingCodeRepository()
        self.devices = FakeDeviceRepository()
        self.reminders = FakeReminderRepository()
        self.fires = FakeFireRepository()
        self.changes = FakeChangeRepository()

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path = tmp_path / "jwt_private.pem"
    public_path = tmp_path / "jwt_public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    return Settings(
        jwt_private_key_path=str(private_path),
        jwt_public_key_path=str(public_path),
        fcm_enabled=False,
        firebase_credentials_path=None,
        firebase_credentials_json=None,
        rate_limit_per_minute=1000,
        cors_origins=["http://testserver"],
    )


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture
def push() -> FakePush:
    return FakePush()


@pytest.fixture
def container(
    settings: Settings,
    clock: FixedClock,
    publisher: FakePublisher,
    push: FakePush,
) -> Iterator[Container]:
    yield Container(
        settings=settings,
        database=FakeDatabase(),  # type: ignore[arg-type]
        redis=FakeRedis(),  # type: ignore[arg-type]
        clock=clock,
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenService(settings, clock),
        publisher=publisher,
        push=push,
        rate_limiter=FakeLimiter(),
    )
