from dataclasses import dataclass
from datetime import datetime

from nova.domain.shared.errors import InvalidTransition
from nova.domain.shared.ids import DeviceId, PairingCodeId, UserId


@dataclass(frozen=True, slots=True)
class PairingCode:
    id: PairingCodeId
    user_id: UserId
    code_hash: str
    expires_at: datetime
    created_at: datetime
    consumed_at: datetime | None = None
    device_id: DeviceId | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.consumed_at is None and self.expires_at > now

    def consume(self, device_id: DeviceId, now: datetime) -> "PairingCode":
        if not self.is_valid(now):
            raise InvalidTransition("pairing code is expired or already used")
        return PairingCode(
            id=self.id,
            user_id=self.user_id,
            code_hash=self.code_hash,
            expires_at=self.expires_at,
            created_at=self.created_at,
            consumed_at=now,
            device_id=device_id,
        )
