from datetime import datetime
from typing import Any


class Clock:
    def now(self) -> datetime: ...


class PasswordHasher:
    def hash(self, raw: str) -> str: ...

    def verify(self, raw: str, hashed: str) -> bool: ...


class TokenClaims:
    def __init__(self, claims: dict[str, Any]) -> None:
        self.claims = claims

    @property
    def subject(self) -> str:
        return str(self.claims["sub"])

    @property
    def audience(self) -> str:
        return str(self.claims["aud"])

    def get(self, name: str) -> Any:
        return self.claims.get(name)


class TokenService:
    def issue_access_token(self, user_id: str, email: str) -> str: ...

    def issue_device_token(self, user_id: str, device_id: str) -> str: ...

    def issue_refresh_token(self) -> tuple[str, str, datetime]: ...

    def decode(self, token: str, audience: str) -> TokenClaims: ...

    def hash_token(self, token: str) -> str: ...

    def generate_pairing_code(self) -> tuple[str, str]: ...

    def jwks(self) -> dict[str, object]: ...
