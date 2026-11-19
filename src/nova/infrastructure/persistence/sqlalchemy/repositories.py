from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova.application.ports.repositories import (
    ChangeRepository,
    DeviceRepository,
    FireRepository,
    PairingCodeRepository,
    RefreshTokenRepository,
    ReminderRepository,
    UserRepository,
)
from nova.domain.device.device import Device
from nova.domain.identity.pairing_code import PairingCode
from nova.domain.identity.refresh_token import RefreshToken
from nova.domain.identity.user import User
from nova.domain.reminder.fire import ReminderFire
from nova.domain.reminder.reminder import Reminder, ReminderStatus
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
from nova.infrastructure.persistence.sqlalchemy.mappers import (
    change_from_model,
    device_from_model,
    pairing_code_from_model,
    refresh_token_from_model,
    reminder_from_model,
    user_from_model,
)
from nova.infrastructure.persistence.sqlalchemy.models import (
    ChangeModel,
    DeviceModel,
    PairingCodeModel,
    RefreshTokenModel,
    ReminderFireModel,
    ReminderModel,
    UserModel,
)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=as_uuid(user.id),
                email=user.email,
                password_hash=user.password_hash,
                created_at=user.created_at,
                is_active=user.is_active,
            )
        )

    async def get(self, user_id: UserId) -> User | None:
        row = await self._session.get(UserModel, as_uuid(user_id))
        return user_from_model(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        row = result.scalar_one_or_none()
        return user_from_model(row) if row else None


class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenModel(
                id=as_uuid(token.id),
                user_id=as_uuid(token.user_id),
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                created_at=token.created_at,
                revoked_at=token.revoked_at,
            )
        )

    async def get(self, token_id: RefreshTokenId) -> RefreshToken | None:
        row = await self._session.get(RefreshTokenModel, as_uuid(token_id))
        return refresh_token_from_model(row) if row else None

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return refresh_token_from_model(row) if row else None

    async def save(self, token: RefreshToken) -> None:
        row = await self._session.get(RefreshTokenModel, as_uuid(token.id))
        if row is not None:
            row.revoked_at = token.revoked_at


class SqlAlchemyPairingCodeRepository(PairingCodeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, code: PairingCode) -> None:
        self._session.add(
            PairingCodeModel(
                id=as_uuid(code.id),
                user_id=as_uuid(code.user_id),
                code_hash=code.code_hash,
                expires_at=code.expires_at,
                created_at=code.created_at,
                consumed_at=code.consumed_at,
                device_id=as_uuid(code.device_id) if code.device_id else None,
            )
        )

    async def get_by_hash(self, code_hash: str) -> PairingCode | None:
        result = await self._session.execute(
            select(PairingCodeModel).where(PairingCodeModel.code_hash == code_hash)
        )
        row = result.scalar_one_or_none()
        return pairing_code_from_model(row) if row else None

    async def save(self, code: PairingCode) -> None:
        row = await self._session.get(PairingCodeModel, as_uuid(code.id))
        if row is not None:
            row.consumed_at = code.consumed_at
            row.device_id = as_uuid(code.device_id) if code.device_id else None


class SqlAlchemyDeviceRepository(DeviceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, device: Device) -> None:
        self._session.add(self._to_model(device))

    async def get(self, device_id: DeviceId) -> Device | None:
        row = await self._session.get(DeviceModel, as_uuid(device_id))
        return device_from_model(row) if row else None

    async def list_for_user(self, user_id: UserId) -> list[Device]:
        result = await self._session.execute(
            select(DeviceModel)
            .where(DeviceModel.user_id == as_uuid(user_id), DeviceModel.revoked_at.is_(None))
            .order_by(DeviceModel.paired_at.desc())
        )
        return [device_from_model(row) for row in result.scalars()]

    async def save(self, device: Device) -> None:
        row = await self._session.get(DeviceModel, as_uuid(device.id))
        if row is None:
            self._session.add(self._to_model(device))
            return
        row.name = device.name
        row.last_state = device.last_state
        row.last_seen_at = device.last_seen_at
        row.app_version = device.app_version
        row.fcm_token = device.fcm_token
        row.revoked_at = device.revoked_at

    async def list_push_tokens(self, user_id: UserId) -> list[str]:
        result = await self._session.execute(
            select(DeviceModel.fcm_token).where(
                DeviceModel.user_id == as_uuid(user_id),
                DeviceModel.fcm_token.is_not(None),
                DeviceModel.revoked_at.is_(None),
            )
        )
        return [token for token in result.scalars() if token]

    @staticmethod
    def _to_model(device: Device) -> DeviceModel:
        return DeviceModel(
            id=as_uuid(device.id),
            user_id=as_uuid(device.user_id),
            name=device.name,
            last_state=device.last_state,
            last_seen_at=device.last_seen_at,
            app_version=device.app_version,
            fcm_token=device.fcm_token,
            paired_at=device.paired_at,
            revoked_at=device.revoked_at,
        )


class SqlAlchemyReminderRepository(ReminderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, reminder: Reminder) -> None:
        self._session.add(self._to_model(reminder))

    async def get(self, user_id: UserId, reminder_id: ReminderId) -> Reminder | None:
        row = await self._session.get(ReminderModel, as_uuid(reminder_id))
        if row is None or row.user_id != as_uuid(user_id):
            return None
        return reminder_from_model(row)

    async def get_by_id(self, reminder_id: ReminderId) -> Reminder | None:
        row = await self._session.get(ReminderModel, as_uuid(reminder_id))
        return reminder_from_model(row) if row else None

    async def list_for_user(
        self,
        user_id: UserId,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Reminder]:
        statement = select(ReminderModel).where(ReminderModel.user_id == as_uuid(user_id))
        if not include_deleted:
            statement = statement.where(ReminderModel.deleted_at.is_(None))
        result = await self._session.execute(
            statement.order_by(ReminderModel.due_at.asc()).limit(limit).offset(offset)
        )
        return [reminder_from_model(row) for row in result.scalars()]

    async def list_due(self, now: datetime, limit: int = 100) -> list[Reminder]:
        result = await self._session.execute(
            select(ReminderModel)
            .where(
                ReminderModel.deleted_at.is_(None),
                ReminderModel.due_at <= now,
                ReminderModel.status.in_([ReminderStatus.PENDING, ReminderStatus.SNOOZED]),
            )
            .limit(limit)
        )
        return [reminder_from_model(row) for row in result.scalars()]

    async def list_scheduled(self, limit: int = 1000) -> list[Reminder]:
        result = await self._session.execute(
            select(ReminderModel)
            .where(
                ReminderModel.deleted_at.is_(None),
                ReminderModel.status.in_([ReminderStatus.PENDING, ReminderStatus.SNOOZED]),
            )
            .limit(limit)
        )
        return [reminder_from_model(row) for row in result.scalars()]

    async def save(self, reminder: Reminder) -> None:
        row = await self._session.get(ReminderModel, as_uuid(reminder.id))
        if row is None:
            self._session.add(self._to_model(reminder))
            return
        row.content = reminder.content.value
        row.due_at = reminder.due_at.value
        row.recurrence = reminder.recurrence.value
        row.status = reminder.status.value
        row.origin = reminder.origin.value
        row.version = reminder.version
        row.updated_at = reminder.updated_at
        row.deleted_at = reminder.deleted_at

    @staticmethod
    def _to_model(reminder: Reminder) -> ReminderModel:
        return ReminderModel(
            id=as_uuid(reminder.id),
            user_id=as_uuid(reminder.user_id),
            content=reminder.content.value,
            due_at=reminder.due_at.value,
            recurrence=reminder.recurrence.value,
            status=reminder.status.value,
            origin=reminder.origin.value,
            version=reminder.version,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            deleted_at=reminder.deleted_at,
        )


class SqlAlchemyFireRepository(FireRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, fire: ReminderFire) -> bool:
        if await self.has(fire.id):
            return False
        self._session.add(
            ReminderFireModel(
                id=as_uuid(fire.id),
                reminder_id=as_uuid(fire.reminder_id),
                user_id=as_uuid(fire.user_id),
                fired_at=fire.fired_at,
            )
        )
        return True

    async def has(self, fire_id: FireId) -> bool:
        row = await self._session.get(ReminderFireModel, as_uuid(fire_id))
        return row is not None


class SqlAlchemyChangeRepository(ChangeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: DomainEvent, payload: dict[str, object]) -> Change:
        version = payload.get("version", 1)
        row = ChangeModel(
            user_id=as_uuid(event.user_id),  # type: ignore[attr-defined]
            aggregate_type=event.event_type.split(".", 1)[0],
            aggregate_id=event.aggregate_id,
            version=int(version) if isinstance(version, int) else 1,
            payload=payload,
            occurred_at=event.occurred_at,
        )
        self._session.add(row)
        await self._session.flush()
        return change_from_model(row)

    async def list_since(
        self,
        user_id: UserId,
        cursor: ChangeId,
        limit: int = 100,
    ) -> list[Change]:
        result = await self._session.execute(
            select(ChangeModel)
            .where(ChangeModel.user_id == as_uuid(user_id), ChangeModel.id > cursor)
            .order_by(ChangeModel.id.asc())
            .limit(limit)
        )
        return [change_from_model(row) for row in result.scalars()]
