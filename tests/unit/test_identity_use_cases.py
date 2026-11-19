from typing import TYPE_CHECKING

import pytest
from tests.conftest import FakePublisher, FakeUnitOfWork

from nova.application.errors import AuthenticationError, ConflictError
from nova.application.identity.use_cases import (
    IssuePairingCode,
    LoginUser,
    PairDevice,
    RegisterUser,
)
from nova.bootstrap import Container

if TYPE_CHECKING:
    from nova.application.identity.dto import PairingCodeResult


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(uow: FakeUnitOfWork, container: Container) -> None:
    use_case = RegisterUser(uow, container.hasher, container.clock)
    await use_case.execute("user@example.com", "password123")
    with pytest.raises(ConflictError):
        await use_case.execute("USER@example.com", "password123")


@pytest.mark.asyncio
async def test_login_returns_tokens_for_valid_credentials(
    uow: FakeUnitOfWork,
    container: Container,
) -> None:
    register = RegisterUser(uow, container.hasher, container.clock)
    await register.execute("user@example.com", "password123")
    tokens = await LoginUser(uow, container.hasher, container.tokens, container.clock).execute(
        "user@example.com", "password123"
    )
    claims = container.tokens.decode(tokens.access_token, container.settings.jwt_user_audience)
    assert claims.subject == str(claims.subject)
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(uow: FakeUnitOfWork, container: Container) -> None:
    register = RegisterUser(uow, container.hasher, container.clock)
    await register.execute("user@example.com", "password123")
    with pytest.raises(AuthenticationError):
        await LoginUser(uow, container.hasher, container.tokens, container.clock).execute(
            "user@example.com", "wrong-password"
        )


@pytest.mark.asyncio
async def test_pairing_code_is_single_use(
    uow: FakeUnitOfWork,
    container: Container,
    publisher: FakePublisher,
) -> None:
    register = RegisterUser(uow, container.hasher, container.clock)
    user_id = await register.execute("user@example.com", "password123")
    result: PairingCodeResult = await IssuePairingCode(
        uow, container.tokens, container.clock
    ).execute(user_id)
    pair = PairDevice(uow, container.tokens, container.clock, publisher)
    device_token = await pair.execute(result.code, "Nova Pi", "1.0.0")
    claims = container.tokens.decode(
        device_token.access_token, container.settings.jwt_device_audience
    )
    assert claims.get("device_id") == str(device_token.device_id)
    with pytest.raises(AuthenticationError):
        await pair.execute(result.code, "Nova Pi", "1.0.0")
