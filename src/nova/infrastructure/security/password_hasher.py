from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from nova.application.ports.security import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._hasher = Argon2Hasher(time_cost=2, memory_cost=19_456, parallelism=1)

    def hash(self, raw: str) -> str:
        return self._hasher.hash(raw)

    def verify(self, raw: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, raw)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
