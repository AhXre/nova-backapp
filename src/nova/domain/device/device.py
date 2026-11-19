from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from nova.domain.device.events import DevicePaired, DeviceRevoked, DeviceStateChanged
from nova.domain.shared.events import AggregateRoot
from nova.domain.shared.ids import DeviceId, UserId, as_uuid


@dataclass(slots=True)
class Device(AggregateRoot):
    id: DeviceId
    user_id: UserId
    name: str
    paired_at: datetime
    last_state: str = "ESPERA"
    last_seen_at: datetime | None = None
    app_version: str | None = None
    fcm_token: str | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        super().__init__()

    @classmethod
    def pair(
        cls,
        device_id: DeviceId,
        user_id: UserId,
        name: str,
        now: datetime,
        app_version: str | None = None,
    ) -> "Device":
        if not name.strip():
            raise ValueError("device name cannot be empty")
        device = cls(
            id=device_id,
            user_id=user_id,
            name=name.strip(),
            paired_at=now,
            last_seen_at=now,
            app_version=app_version,
        )
        device.raise_event(
            DevicePaired(
                event_id=uuid4(),
                occurred_at=now,
                device_id=as_uuid(device_id),
                user_id=as_uuid(user_id),
            )
        )
        return device

    def update_state(self, state: str, now: datetime, app_version: str | None = None) -> None:
        if self.revoked_at is not None:
            raise ValueError("cannot update a revoked device")
        self.last_state = state
        self.last_seen_at = now
        if app_version is not None:
            self.app_version = app_version
        self.raise_event(
            DeviceStateChanged(
                event_id=uuid4(),
                occurred_at=now,
                device_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
                state=state,
            )
        )

    def update_push_token(self, token: str) -> None:
        if self.revoked_at is not None:
            raise ValueError("cannot update a revoked device")
        if not token.strip():
            raise ValueError("fcm token cannot be empty")
        self.fcm_token = token.strip()

    def revoke(self, now: datetime) -> None:
        if self.revoked_at is not None:
            raise ValueError("device already revoked")
        self.revoked_at = now
        self.raise_event(
            DeviceRevoked(
                event_id=uuid4(),
                occurred_at=now,
                device_id=as_uuid(self.id),
                user_id=as_uuid(self.user_id),
            )
        )
