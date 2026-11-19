from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nova.application.errors import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from nova.bootstrap import Container, build_container
from nova.domain.shared.errors import DomainError
from nova.infrastructure.config import Settings, get_settings
from nova.infrastructure.logging import configure_logging
from nova.interface.api.v1 import auth, devices, health, reminders, sync
from nova.interface.api.v1.deps import websocket_identity
from nova.interface.websocket.hub import WebSocketHub

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI, container: Container) -> AsyncIterator[None]:
    app.state.container = container
    app.state.hub = WebSocketHub(container.redis)
    try:
        yield
    finally:
        await container.close()


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")
    actual_container = container or build_container(settings)

    @asynccontextmanager
    async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with lifespan(app, actual_container):
            yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend de sincronización para el Asistente Tecnológico Inteligente.",
        lifespan=app_lifespan,
        docs_url="/docs" if settings.docs_enabled or settings.environment != "production" else None,
        redoc_url="/redoc"
        if settings.docs_enabled or settings.environment != "production"
        else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Sec-WebSocket-Protocol"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: object) -> object:
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(AuthenticationError)
    async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(DomainError)
    async def domain_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ApplicationError)
    async def application_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    for module in (health, auth, devices, reminders, sync):
        app.include_router(module.router, prefix=API_PREFIX)

    @app.websocket("/ws/v1/events")
    async def events_socket(websocket: WebSocket) -> None:
        try:
            user_id = await websocket_identity(
                actual_container, websocket.headers.get("sec-websocket-protocol")
            )
        except HTTPException:
            await websocket.close(code=4401)
            return
        hub: WebSocketHub = websocket.app.state.hub
        await hub.connect(user_id, websocket)
        await hub.serve(user_id, websocket)

    return app
