from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from tests.conftest import FakeUnitOfWork

from nova.bootstrap import Container
from nova.interface.http.app import create_app


@pytest.mark.asyncio
async def test_auth_reminders_sync_and_openapi(
    container: Container,
    uow: FakeUnitOfWork,
) -> None:
    object.__setattr__(container, "uow", lambda: uow)
    app = create_app(settings=container.settings, container=container)
    app.state.container = container

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 201
        UUID(response.json()["user_id"])

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        tokens = response.json()
        user_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = await client.post("/api/v1/auth/pairing-code", headers=user_headers)
        assert response.status_code == 200
        pairing_code = response.json()["code"]

        response = await client.post(
            "/api/v1/auth/pair",
            json={"code": pairing_code, "name": "Nova Pi", "app_version": "1.0.0"},
        )
        assert response.status_code == 200
        device_token = response.json()["access_token"]
        device_headers = {"Authorization": f"Bearer {device_token}"}

        response = await client.patch(
            "/api/v1/devices/me/push-token",
            headers=device_headers,
            json={"token": "fcm-token"},
        )
        assert response.status_code == 204

        response = await client.post(
            "/api/v1/reminders",
            headers=user_headers,
            json={
                "content": "Recuérdame llamar al dentista",
                "due_at": "2026-11-20T17:00:00Z",
                "origin": "device",
            },
        )
        assert response.status_code == 201
        reminder = response.json()
        assert reminder["status"] == "pending"

        response = await client.get("/api/v1/reminders", headers=user_headers)
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [reminder["id"]]

        response = await client.get("/api/v1/sync?since=0", headers=user_headers)
        assert response.status_code == 200
        sync = response.json()
        assert sync["next_cursor"] >= 1
        assert sync["changes"][0]["payload"]["event_type"] == "device.paired"

        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert "/api/v1/reminders" in response.json()["paths"]
