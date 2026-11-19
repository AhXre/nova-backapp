from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID, uuid4

from nova.application.errors import AuthenticationError, ConflictError, NotFoundError
from nova.application.events import record_events
from nova.application.identity.dto import (
    DeviceTokenResult,
    DeviceView,
    PairingCodeResult,
    TokenPair,
)
from nova.application.ports.events import EventPublisher
from nova.application.ports.security import Clock, PasswordHasher, TokenService
from nova.application.ports.uow import UnitOfWork
from nova.domain.device.device import Device
from nova.domain.identity.pairing_code import PairingCode
from nova.domain.identity.refresh_token import RefreshToken
from nova.domain.identity.user import User
from nova.domain.shared.ids import (
    DeviceId,
    PairingCodeId,
    RefreshTokenId,
    UserId,
    as_uuid,
    new_device_id,
    new_user_id,
)

ACCESS_TTL_SECONDS = 900
PAIRING_TTL = timedelta(minutes=5)


async def _issue_token_pair(
    uow: UnitOfWork,
    tokens: TokenService,
    clock: Clock,
    user: User,
) -> TokenPair:
    raw, token_hash, expires_at = tokens.issue_refresh_token()
    token = RefreshToken(
        id=RefreshTokenId(uuid4()),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=clock.now(),
    )
    await uow.refresh_tokens.add(token)
    await uow.commit()
    return TokenPair(
        access_token=tokens.issue_access_token(str(user.id), user.email),
        refresh_token=raw,
        expires_in=ACCESS_TTL_SECONDS,
    )


class RegisterUser:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher, clock: Clock) -> None:
        self._uow = uow
        self._hasher = hasher
        self._clock = clock

    async def execute(self, email: str, password: str) -> UUID:
        normalized = email.strip().lower()
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if await self._uow.users.get_by_email(normalized) is not None:
            raise ConflictError("email already registered")
        now = self._clock.now()
        user = User(
            id=new_user_id(),
            email=normalized,
            password_hash=self._hasher.hash(password),
            created_at=now,
        )
        await self._uow.users.add(user)
        await self._uow.commit()
        return as_uuid(user.id)


class LoginUser:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    async def execute(self, email: str, password: str) -> TokenPair:
        user = await self._uow.users.get_by_email(email.strip().lower())
        if (
            user is None
            or not user.is_active
            or not self._hasher.verify(password, user.password_hash)
        ):
            raise AuthenticationError("invalid credentials")
        return await _issue_token_pair(self._uow, self._tokens, self._clock, user)


class RefreshTokens:
    def __init__(
        self,
        uow: UnitOfWork,
        tokens: TokenService,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._tokens = tokens
        self._clock = clock

    async def execute(self, raw_token: str) -> TokenPair:
        token_hash = self._tokens.hash_token(raw_token)
        stored = await self._uow.refresh_tokens.get_by_hash(token_hash)
        if stored is None or not stored.is_valid(self._clock.now()):
            raise AuthenticationError("invalid or expired refresh token")
        user = await self._uow.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("user is no longer active")
        await self._uow.refresh_tokens.save(stored.revoke(self._clock.now()))
        return await _issue_token_pair(self._uow, self._tokens, self._clock, user)


class Logout:
    def __init__(self, uow: UnitOfWork, tokens: TokenService, clock: Clock) -> None:
        self._uow = uow
        self._tokens = tokens
        self._clock = clock

    async def execute(self, raw_token: str) -> None:
        stored = await self._uow.refresh_tokens.get_by_hash(self._tokens.hash_token(raw_token))
        if stored is not None and stored.is_valid(self._clock.now()):
            await self._uow.refresh_tokens.save(stored.revoke(self._clock.now()))
            await self._uow.commit()


class IssuePairingCode:
    def __init__(self, uow: UnitOfWork, tokens: TokenService, clock: Clock) -> None:
        self._uow = uow
        self._tokens = tokens
        self._clock = clock

    async def execute(self, user_id: UUID) -> PairingCodeResult:
        raw, code_hash = self._tokens.generate_pairing_code()
        now = self._clock.now()
        code = PairingCode(
            id=PairingCodeId(uuid4()),
            user_id=UserId(user_id),
            code_hash=code_hash,
            expires_at=now + PAIRING_TTL,
            created_at=now,
        )
        await self._uow.pairing_codes.add(code)
        await self._uow.commit()
        return PairingCodeResult(code=raw, expires_at=code.expires_at)


class PairDevice:
    def __init__(
        self,
        uow: UnitOfWork,
        tokens: TokenService,
        clock: Clock,
        publisher: EventPublisher,
    ) -> None:
        self._uow = uow
        self._tokens = tokens
        self._clock = clock
        self._publisher = publisher

    async def execute(
        self,
        code: str,
        name: str,
        app_version: str | None = None,
    ) -> DeviceTokenResult:
        code_hash = self._tokens.hash_token(code)
        pairing = await self._uow.pairing_codes.get_by_hash(code_hash)
        now = self._clock.now()
        if pairing is None or not pairing.is_valid(now):
            raise AuthenticationError("invalid or expired pairing code")
        user_id = pairing.user_id
        device_id = new_device_id()
        device = Device.pair(device_id, user_id, name, now, app_version)
        await self._uow.pairing_codes.save(pairing.consume(device_id, now))
        await self._uow.devices.add(device)
        events = device.pull_events()
        await record_events(self._uow, events)
        await self._uow.commit()
        await self._publisher.publish_many(events)
        return DeviceTokenResult(
            access_token=self._tokens.issue_device_token(str(user_id), str(device_id)),
            device_id=as_uuid(device_id),
        )


class ListDevices:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> Sequence[DeviceView]:
        devices = await self._uow.devices.list_for_user(UserId(user_id))
        return [
            DeviceView(
                id=as_uuid(device.id),
                name=device.name,
                last_state=device.last_state,
                last_seen_at=device.last_seen_at,
                app_version=device.app_version,
                paired_at=device.paired_at,
                revoked_at=device.revoked_at,
            )
            for device in devices
        ]


class UpdateDeviceState:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(
        self,
        user_id: UUID,
        device_id: UUID,
        state: str,
        app_version: str | None = None,
    ) -> None:
        device = await self._uow.devices.get(DeviceId(device_id))
        if device is None or device.user_id != UserId(user_id):
            raise NotFoundError("device not found")
        device.update_state(state, self._clock.now(), app_version)
        events = device.pull_events()
        await record_events(self._uow, events)
        await self._uow.commit()
        await self._publisher.publish_many(events)


class RegisterPushToken:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, device_id: UUID, token: str) -> None:
        device = await self._uow.devices.get(DeviceId(device_id))
        if device is None or device.user_id != UserId(user_id):
            raise NotFoundError("device not found")
        device.update_push_token(token)
        await self._uow.devices.save(device)
        await self._uow.commit()


class RevokeDevice:
    def __init__(self, uow: UnitOfWork, clock: Clock, publisher: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._publisher = publisher

    async def execute(self, user_id: UUID, device_id: UUID) -> None:
        device = await self._uow.devices.get(DeviceId(device_id))
        if device is None or device.user_id != UserId(user_id):
            raise NotFoundError("device not found")
        device.revoke(self._clock.now())
        events = device.pull_events()
        await record_events(self._uow, events)
        await self._uow.commit()
        await self._publisher.publish_many(events)
