from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from nova.application.ports.uow import UnitOfWork
from nova.bootstrap import Container
from nova.interface.api.v1.deps import (
    current_user_id,
    enforce_rate_limit,
    get_container,
    get_uow,
)
from nova.interface.api.v1.schemas import (
    DeviceTokenResponse,
    LoginRequest,
    PairDeviceRequest,
    PairingCodeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
    _: None = Depends(enforce_rate_limit),
) -> dict[str, UUID]:
    user_id = await container.identity(uow).register.execute(payload.email, payload.password)
    return {"user_id": user_id}


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
    _: None = Depends(enforce_rate_limit),
) -> TokenResponse:
    tokens = await container.identity(uow).login.execute(payload.email, payload.password)
    return TokenResponse.model_validate(tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
    _: None = Depends(enforce_rate_limit),
) -> TokenResponse:
    tokens = await container.identity(uow).refresh.execute(payload.refresh_token)
    return TokenResponse.model_validate(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> Response:
    await container.identity(uow).logout.execute(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/pairing-code", response_model=PairingCodeResponse)
async def issue_pairing_code(
    user_id: UUID = Depends(current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> PairingCodeResponse:
    result = await container.identity(uow).issue_pairing_code.execute(user_id)
    return PairingCodeResponse.model_validate(result)


@router.post("/pair", response_model=DeviceTokenResponse)
async def pair_device(
    payload: PairDeviceRequest,
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
    _: None = Depends(enforce_rate_limit),
) -> DeviceTokenResponse:
    result = await container.identity(uow).pair_device.execute(
        payload.code,
        payload.name,
        payload.app_version,
    )
    return DeviceTokenResponse.model_validate(result)


@router.get("/.well-known/jwks.json", include_in_schema=False)
async def jwks(container: Container = Depends(get_container)) -> dict[str, object]:
    return container.tokens.jwks()
