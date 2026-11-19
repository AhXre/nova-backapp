from uuid import UUID

from fastapi import APIRouter, Depends, status

from nova.application.ports.uow import UnitOfWork
from nova.bootstrap import Container
from nova.interface.api.v1.deps import current_device, current_user_id, get_container, get_uow
from nova.interface.api.v1.schemas import DeviceResponse, DeviceStateRequest, PushTokenRequest

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    user_id: UUID = Depends(current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> list[DeviceResponse]:
    devices = await container.identity(uow).list_devices.execute(user_id)
    return [DeviceResponse.model_validate(device) for device in devices]


@router.patch("/me/state", status_code=status.HTTP_204_NO_CONTENT)
async def update_state(
    payload: DeviceStateRequest,
    identity: tuple[UUID, UUID] = Depends(current_device),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> None:
    user_id, device_id = identity
    await container.identity(uow).update_device_state.execute(
        user_id, device_id, payload.state, payload.app_version
    )


@router.patch("/me/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def register_push_token(
    payload: PushTokenRequest,
    identity: tuple[UUID, UUID] = Depends(current_device),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> None:
    user_id, device_id = identity
    await container.identity(uow).register_push_token.execute(user_id, device_id, payload.token)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device(
    device_id: UUID,
    user_id: UUID = Depends(current_user_id),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> None:
    await container.identity(uow).revoke_device.execute(user_id, device_id)
