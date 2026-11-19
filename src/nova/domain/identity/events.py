from dataclasses import dataclass
from uuid import UUID

from nova.domain.shared.events import DomainEvent


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    user_id: UUID
    email: str

    @property
    def event_type(self) -> str:
        return "user.registered"

    @property
    def aggregate_id(self) -> UUID:
        return self.user_id
