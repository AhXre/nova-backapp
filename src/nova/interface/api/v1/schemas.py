from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from nova.domain.reminder.reminder import ReminderOrigin, ReminderStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=256)


class TokenResponse(ORMModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class PairingCodeResponse(ORMModel):
    code: str
    expires_at: datetime


class PairDeviceRequest(BaseModel):
    code: str = Field(min_length=6, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    app_version: str | None = Field(default=None, max_length=64)


class DeviceTokenResponse(ORMModel):
    access_token: str
    device_id: UUID


class PushTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class DeviceStateRequest(BaseModel):
    state: str = Field(min_length=1, max_length=32)
    app_version: str | None = Field(default=None, max_length=64)


class DeviceResponse(ORMModel):
    id: UUID
    name: str
    last_state: str
    last_seen_at: datetime | None
    app_version: str | None
    paired_at: datetime
    revoked_at: datetime | None


class ReminderCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    due_at: datetime
    recurrence: str | None = Field(default=None, max_length=255)
    origin: ReminderOrigin = ReminderOrigin.MOBILE


class ReminderUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    due_at: datetime
    recurrence: str | None = Field(default=None, max_length=255)
    expected_version: int | None = Field(default=None, ge=1)


class SnoozeRequest(BaseModel):
    snooze_until: datetime
    expected_version: int | None = Field(default=None, ge=1)


class ReminderResponse(ORMModel):
    id: UUID
    user_id: UUID
    content: str
    due_at: datetime
    recurrence: str | None
    status: ReminderStatus
    origin: ReminderOrigin
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class SyncChangeResponse(ORMModel):
    id: int
    aggregate_type: str
    aggregate_id: UUID
    version: int
    payload: dict[str, object]
    occurred_at: datetime


class SyncResponse(ORMModel):
    changes: list[SyncChangeResponse]
    next_cursor: int


class HealthResponse(BaseModel):
    status: str
    service: str
