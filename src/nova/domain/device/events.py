from dataclasses import dataclass
from uuid import UUID

from nova.domain.shared.events import DomainEvent


@dataclass(frozen=True, slots=True)
class DevicePaired(DomainEvent):
    device_id: UUID
    user_id: UUID

    @property
    def event_type(self) -> str:
        return "device.paired"

    @property
    def aggregate_id(self) -> UUID:
        return self.device_id


@dataclass(frozen=True, slots=True)
class DeviceRevoked(DomainEvent):
    device_id: UUID
    user_id: UUID

    @property
    def event_type(self) -> str:
        return "device.revoked"

    @property
    def aggregate_id(self) -> UUID:
        return self.device_id


@dataclass(frozen=True, slots=True)
class DeviceStateChanged(DomainEvent):
    device_id: UUID
    user_id: UUID
    state: str

    @property
    def event_type(self) -> str:
        return "device.state"

    @property
    def aggregate_id(self) -> UUID:
        return self.device_id
