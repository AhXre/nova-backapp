from dataclasses import dataclass

from redis.asyncio import Redis

from nova.application.identity.use_cases import (
    IssuePairingCode,
    ListDevices,
    LoginUser,
    Logout,
    PairDevice,
    RefreshTokens,
    RegisterPushToken,
    RegisterUser,
    RevokeDevice,
    UpdateDeviceState,
)
from nova.application.ports.events import EventPublisher
from nova.application.ports.push import PushNotifier
from nova.application.ports.rate_limit import RateLimiter
from nova.application.ports.security import Clock, PasswordHasher, TokenService
from nova.application.ports.uow import UnitOfWork
from nova.application.reminder.use_cases import (
    CreateReminder,
    DeleteReminder,
    FireReminder,
    GetReminder,
    ListReminders,
    MarkReminderDone,
    SnoozeReminder,
    UpdateReminder,
)
from nova.application.sync.use_cases import GetChanges
from nova.infrastructure.config import Settings
from nova.infrastructure.events.redis_event_bus import RedisEventPublisher
from nova.infrastructure.persistence.database import Database
from nova.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork
from nova.infrastructure.push.fcm_push import FcmPushNotifier
from nova.infrastructure.rate_limit.redis_rate_limiter import RedisRateLimiter
from nova.infrastructure.security.jwt_service import JwtTokenService, SystemClock
from nova.infrastructure.security.password_hasher import Argon2PasswordHasher


@dataclass(frozen=True)
class IdentityUseCases:
    register: RegisterUser
    login: LoginUser
    refresh: RefreshTokens
    logout: Logout
    issue_pairing_code: IssuePairingCode
    pair_device: PairDevice
    list_devices: ListDevices
    update_device_state: UpdateDeviceState
    register_push_token: RegisterPushToken
    revoke_device: RevokeDevice


@dataclass(frozen=True)
class ReminderUseCases:
    create: CreateReminder
    get: GetReminder
    list: ListReminders
    update: UpdateReminder
    delete: DeleteReminder
    snooze: SnoozeReminder
    done: MarkReminderDone
    fire: FireReminder


@dataclass(frozen=True)
class SyncUseCases:
    get_changes: GetChanges


@dataclass(frozen=True)
class Container:
    settings: Settings
    database: Database
    redis: Redis
    clock: Clock
    hasher: PasswordHasher
    tokens: TokenService
    publisher: EventPublisher
    push: PushNotifier
    rate_limiter: RateLimiter

    def uow(self) -> SqlAlchemyUnitOfWork:
        return self.database.uow()

    def identity(self, uow: UnitOfWork) -> IdentityUseCases:
        return IdentityUseCases(
            register=RegisterUser(uow, self.hasher, self.clock),
            login=LoginUser(uow, self.hasher, self.tokens, self.clock),
            refresh=RefreshTokens(uow, self.tokens, self.clock),
            logout=Logout(uow, self.tokens, self.clock),
            issue_pairing_code=IssuePairingCode(uow, self.tokens, self.clock),
            pair_device=PairDevice(uow, self.tokens, self.clock, self.publisher),
            list_devices=ListDevices(uow),
            update_device_state=UpdateDeviceState(uow, self.clock, self.publisher),
            register_push_token=RegisterPushToken(uow),
            revoke_device=RevokeDevice(uow, self.clock, self.publisher),
        )

    def reminders(self, uow: UnitOfWork) -> ReminderUseCases:
        return ReminderUseCases(
            create=CreateReminder(uow, self.clock, self.publisher),
            get=GetReminder(uow),
            list=ListReminders(uow),
            update=UpdateReminder(uow, self.clock, self.publisher),
            delete=DeleteReminder(uow, self.clock, self.publisher),
            snooze=SnoozeReminder(uow, self.clock, self.publisher),
            done=MarkReminderDone(uow, self.clock, self.publisher),
            fire=FireReminder(uow, self.clock, self.publisher, self.push),
        )

    def sync(self, uow: UnitOfWork) -> SyncUseCases:
        return SyncUseCases(get_changes=GetChanges(uow))

    async def close(self) -> None:
        await self.redis.aclose()
        await self.database.dispose()


def build_container(settings: Settings) -> Container:
    clock = SystemClock()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return Container(
        settings=settings,
        database=Database(settings.database_url, echo=settings.debug),
        redis=redis,
        clock=clock,
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenService(settings, clock),
        publisher=RedisEventPublisher(redis),
        push=FcmPushNotifier(settings),
        rate_limiter=RedisRateLimiter(redis),
    )
