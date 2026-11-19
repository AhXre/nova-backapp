from dataclasses import dataclass
from datetime import datetime

from nova.domain.shared.errors import InvalidTransition
from nova.domain.shared.ids import RefreshTokenId, UserId


@dataclass(frozen=True, slots=True)
class RefreshToken:
    id: RefreshTokenId
    user_id: UserId
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now

    def revoke(self, now: datetime) -> "RefreshToken":
        if self.revoked_at is not None:
            raise InvalidTransition("refresh token already revoked")
        return RefreshToken(
            id=self.id,
            user_id=self.user_id,
            token_hash=self.token_hash,
            expires_at=self.expires_at,
            created_at=self.created_at,
            revoked_at=now,
        )
