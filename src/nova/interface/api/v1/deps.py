from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from nova.application.errors import RateLimitError
from nova.application.ports.uow import UnitOfWork
from nova.bootstrap import Container

bearer_scheme = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container: Container | None = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("container is not configured")
    return container


async def get_uow(
    container: Container = Depends(get_container),
) -> AsyncIterator[UnitOfWork]:
    async with container.uow() as uow:
        yield uow


async def enforce_rate_limit(
    request: Request,
    container: Container = Depends(get_container),
) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"ratelimit:{request.url.path}:{client}"
    allowed = await container.rate_limiter.allow(key, container.settings.rate_limit_per_minute, 60)
    if not allowed:
        raise RateLimitError("too many requests")


async def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    container: Container = Depends(get_container),
) -> UUID:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        claims = container.tokens.decode(
            credentials.credentials, container.settings.jwt_user_audience
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc
    return UUID(claims.subject)


async def current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    container: Container = Depends(get_container),
) -> tuple[UUID, UUID]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        claims = container.tokens.decode(
            credentials.credentials, container.settings.jwt_device_audience
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc
    device_id = claims.get("device_id")
    if device_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="device token required"
        )
    return UUID(claims.subject), UUID(str(device_id))


async def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    container: Container = Depends(get_container),
) -> UUID:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    for audience in (container.settings.jwt_user_audience, container.settings.jwt_device_audience):
        try:
            claims = container.tokens.decode(credentials.credentials, audience)
            return UUID(claims.subject)
        except Exception:
            continue
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")


async def websocket_identity(
    container: Container,
    protocols: str | None,
) -> UUID:
    parts = [part.strip() for part in (protocols or "").split(",")]
    if len(parts) < 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer subprotocol required"
        )
    try:
        claims = container.tokens.decode(parts[1], container.settings.jwt_device_audience)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc
    return UUID(claims.subject)


def pagination_params(limit: int = 100, offset: int = 0) -> tuple[int, int]:
    return max(1, min(limit, 500)), max(0, offset)
