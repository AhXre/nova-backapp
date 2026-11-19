# Nova Backend

Backend FastAPI para el Asistente Tecnológico Inteligente: REST + OpenAPI, WebSocket,
PostgreSQL, Redis, APScheduler y FCM, organizado en capas DDD.

## Estructura

```
src/nova/domain        entidades, value objects y eventos (sin frameworks)
src/nova/application   casos de uso y puertos (Protocol)
src/nova/infrastructure adaptadores: SQLAlchemy, Redis, FCM, JWT, APScheduler
src/nova/interface     routers HTTP, WebSockets y esquemas
```

Las dependencias apuntan hacia adentro: `interface → application → domain` e
`infrastructure → application → domain`. Ver `AGENTS.md`.

## Arranque local

```bash
uv sync
cp .env.example .env
./scripts/generate_dev_keys.sh
docker compose up --build
```

Coloca tu cuenta de servicio de Firebase en `secrets/firebase-service-account.json`
(o usa `FIREBASE_CREDENTIALS_JSON` con el JSON en base64). Nunca subas estos archivos.

- API: `https://localhost/api/v1`
- OpenAPI: `https://localhost/openapi.json`
- Docs: `https://localhost/docs`
- WebSocket: `wss://localhost/ws/v1/events` con `Sec-WebSocket-Protocol: bearer, <jwt>`

## Calidad

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
docker compose config
```
