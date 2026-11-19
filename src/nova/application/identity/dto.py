from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900


@dataclass(frozen=True, slots=True)
class PairingCodeResult:
    code: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class DeviceTokenResult:
    access_token: str
    device_id: UUID


@dataclass(frozen=True, slots=True)
class DeviceView:
    id: UUID
    name: str
    last_state: str
    last_seen_at: datetime | None
    app_version: str | None
    paired_at: datetime
    revoked_at: datetime | None
