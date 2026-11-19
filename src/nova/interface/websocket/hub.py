import asyncio
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from nova.infrastructure.events.redis_event_bus import EVENT_CHANNEL_PREFIX


class WebSocketHub:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._connections: dict[UUID, set[WebSocket]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept(subprotocol="bearer")
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    async def serve(self, user_id: UUID, websocket: WebSocket) -> None:
        channel = f"{EVENT_CHANNEL_PREFIX}:{user_id}"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)

        async def pump() -> None:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                await websocket.send_text(str(message["data"]))

        task = asyncio.create_task(pump())
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()  # type: ignore[no-untyped-call]
            self.disconnect(user_id, websocket)
