from datetime import UTC, datetime
from typing import NewType
from uuid import UUID, uuid4

UserId = NewType("UserId", UUID)
DeviceId = NewType("DeviceId", UUID)
ReminderId = NewType("ReminderId", UUID)
PairingCodeId = NewType("PairingCodeId", UUID)
RefreshTokenId = NewType("RefreshTokenId", UUID)
FireId = NewType("FireId", UUID)
ChangeId = NewType("ChangeId", int)


def new_user_id() -> UserId:
    return UserId(uuid4())


def new_device_id() -> DeviceId:
    return DeviceId(uuid4())


def new_reminder_id() -> ReminderId:
    return ReminderId(uuid4())


def new_fire_id() -> FireId:
    return FireId(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)
