from dataclasses import dataclass
from datetime import datetime

from nova.domain.shared.ids import UserId


@dataclass(frozen=True, slots=True)
class User:
    id: UserId
    email: str
    password_hash: str
    created_at: datetime
    is_active: bool = True

    def change_password(self, password_hash: str) -> "User":
        if not password_hash:
            raise ValueError("password_hash cannot be empty")
        return User(
            id=self.id,
            email=self.email,
            password_hash=password_hash,
            created_at=self.created_at,
            is_active=self.is_active,
        )
