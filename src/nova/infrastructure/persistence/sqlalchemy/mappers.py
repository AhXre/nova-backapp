from nova.domain.device.device import Device
from nova.domain.identity.pairing_code import PairingCode
from nova.domain.identity.refresh_token import RefreshToken
from nova.domain.identity.user import User
from nova.domain.reminder.fire import ReminderFire
from nova.domain.reminder.reminder import Reminder, ReminderOrigin, ReminderStatus
from nova.domain.reminder.value_objects import DueAt, RecurrenceRule, ReminderContent
from nova.domain.shared.ids import (
    ChangeId,
    DeviceId,
    FireId,
    PairingCodeId,
    RefreshTokenId,
    ReminderId,
    UserId,
)
from nova.domain.sync.change import Change
from nova.infrastructure.persistence.sqlalchemy.models import (
    ChangeModel,
    DeviceModel,
    PairingCodeModel,
    RefreshTokenModel,
    ReminderFireModel,
    ReminderModel,
    UserModel,
)


def user_from_model(row: UserModel) -> User:
    return User(
        id=UserId(row.id),
        email=row.email,
        password_hash=row.password_hash,
        created_at=row.created_at,
        is_active=row.is_active,
    )


def refresh_token_from_model(row: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=RefreshTokenId(row.id),
        user_id=UserId(row.user_id),
        token_hash=row.token_hash,
        expires_at=row.expires_at,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


def pairing_code_from_model(row: PairingCodeModel) -> PairingCode:
    return PairingCode(
        id=PairingCodeId(row.id),
        user_id=UserId(row.user_id),
        code_hash=row.code_hash,
        expires_at=row.expires_at,
        created_at=row.created_at,
        consumed_at=row.consumed_at,
        device_id=DeviceId(row.device_id) if row.device_id else None,
    )


def device_from_model(row: DeviceModel) -> Device:
    return Device(
        id=DeviceId(row.id),
        user_id=UserId(row.user_id),
        name=row.name,
        paired_at=row.paired_at,
        last_state=row.last_state,
        last_seen_at=row.last_seen_at,
        app_version=row.app_version,
        fcm_token=row.fcm_token,
        revoked_at=row.revoked_at,
    )


def reminder_from_model(row: ReminderModel) -> Reminder:
    return Reminder(
        id=ReminderId(row.id),
        user_id=UserId(row.user_id),
        content=ReminderContent(row.content),
        due_at=DueAt(row.due_at),
        recurrence=RecurrenceRule(row.recurrence),
        status=ReminderStatus(row.status),
        origin=ReminderOrigin(row.origin),
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def fire_from_model(row: ReminderFireModel) -> ReminderFire:
    return ReminderFire(
        id=FireId(row.id),
        reminder_id=ReminderId(row.reminder_id),
        user_id=UserId(row.user_id),
        fired_at=row.fired_at,
    )


def change_from_model(row: ChangeModel) -> Change:
    return Change(
        id=ChangeId(row.id),
        user_id=UserId(row.user_id),
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        version=row.version,
        payload=dict(row.payload),
        occurred_at=row.occurred_at,
    )
