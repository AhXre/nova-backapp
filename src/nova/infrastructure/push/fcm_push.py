import asyncio
import base64
import json
from collections.abc import Mapping, Sequence

import firebase_admin
from firebase_admin import credentials, messaging

from nova.application.ports.push import PushNotifier
from nova.infrastructure.config import Settings


class FcmPushNotifier(PushNotifier):
    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.fcm_enabled
        if not self._enabled:
            return
        if settings.firebase_credentials_json:
            raw = base64.b64decode(settings.firebase_credentials_json)
            certificate = credentials.Certificate(json.loads(raw))
        elif settings.firebase_credentials_path:
            certificate = credentials.Certificate(settings.firebase_credentials_path)
        else:
            raise ValueError("FCM credentials are required when FCM is enabled")
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(certificate)

    async def send(
        self,
        tokens: Sequence[str],
        title: str,
        body: str,
        data: Mapping[str, str] | None = None,
    ) -> list[str]:
        if not self._enabled or not tokens:
            return []
        message = messaging.MulticastMessage(
            tokens=list(tokens),
            notification=messaging.Notification(title=title, body=body),
            data=dict(data or {}),
        )
        response = await asyncio.to_thread(messaging.send_each_for_multicast, message)
        invalid: list[str] = []
        for token, result in zip(tokens, response.responses, strict=False):
            if result.success:
                continue
            error = result.exception
            if isinstance(error, messaging.UnregisteredError):
                invalid.append(token)
        return invalid
