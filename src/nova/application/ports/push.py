from collections.abc import Mapping, Sequence


class PushNotifier:
    async def send(
        self,
        tokens: Sequence[str],
        title: str,
        body: str,
        data: Mapping[str, str] | None = None,
    ) -> list[str]:
        """Send a push notification and return the tokens that were invalidated."""
        ...
