import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from secrets import token_urlsafe

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from nova.application.ports.security import Clock, TokenClaims, TokenService
from nova.infrastructure.config import Settings


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class JwtTokenService(TokenService):
    def __init__(self, settings: Settings, clock: Clock | None = None) -> None:
        self._private_key = Path(settings.jwt_private_key_path).read_text(encoding="utf-8")
        self._public_key = Path(settings.jwt_public_key_path).read_text(encoding="utf-8")
        self._issuer = settings.jwt_issuer
        self._user_audience = settings.jwt_user_audience
        self._device_audience = settings.jwt_device_audience
        self._ttl = settings.access_token_ttl_seconds
        self._clock = clock or SystemClock()

    def issue_access_token(self, user_id: str, email: str) -> str:
        now = self._clock.now()
        return jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "aud": self._user_audience,
                "iss": self._issuer,
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(seconds=self._ttl),
                "typ": "access",
            },
            self._private_key,
            algorithm="RS256",
        )

    def issue_device_token(self, user_id: str, device_id: str) -> str:
        now = self._clock.now()
        return jwt.encode(
            {
                "sub": user_id,
                "device_id": device_id,
                "aud": self._device_audience,
                "iss": self._issuer,
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(days=30),
                "typ": "device",
            },
            self._private_key,
            algorithm="RS256",
        )

    def issue_refresh_token(self) -> tuple[str, str, datetime]:
        raw = token_urlsafe(48)
        return raw, self.hash_token(raw), self._clock.now() + timedelta(days=7)

    def decode(self, token: str, audience: str) -> TokenClaims:
        claims = jwt.decode(
            token,
            self._public_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=self._issuer,
            options={"require": ["sub", "aud", "iss", "exp"]},
        )
        return TokenClaims(claims)

    def hash_token(self, token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    def generate_pairing_code(self) -> tuple[str, str]:
        raw = token_urlsafe(6).upper()[:8]
        return raw, self.hash_token(raw)

    def jwks(self) -> dict[str, object]:
        public_key = serialization.load_pem_public_key(self._public_key.encode("utf-8"))
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValueError("JWT public key must be RSA")
        key = json.loads(RSAAlgorithm.to_jwk(public_key))
        key["kid"] = "nova-2026-1"
        key["use"] = "sig"
        key["alg"] = "RS256"
        return {"keys": [key]}
