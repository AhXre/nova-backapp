from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from nova.application.ports.uow import UnitOfWork
from nova.application.reminder.dto import (
    CreateReminderCommand,
    SnoozeReminderCommand,
    UpdateReminderCommand,
)
from nova.bootstrap import Container
from nova.interface.api.v1.deps import current_principal, get_container, get_uow
from nova.interface.api.v1.schemas import (
    ReminderCreateRequest,
    ReminderResponse,
    ReminderUpdateRequest,
    SnoozeRequest,
)

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreateRequest,
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> ReminderResponse:
    command = CreateReminderCommand(
        user_id=user_id,
        content=payload.content,
        due_at=payload.due_at,
        recurrence=payload.recurrence,
        origin=payload.origin,
    )
    result = await container.reminders(uow).create.execute(command)
    return ReminderResponse.model_validate(result)


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> list[ReminderResponse]:
    results = await container.reminders(uow).list.execute(user_id, limit=limit, offset=offset)
    return [ReminderResponse.model_validate(result) for result in results]


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: UUID,
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> ReminderResponse:
    result = await container.reminders(uow).get.execute(user_id, reminder_id)
    return ReminderResponse.model_validate(result)


@router.patch("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: UUID,
    payload: ReminderUpdateRequest,
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> ReminderResponse:
    command = UpdateReminderCommand(
        user_id=user_id,
        reminder_id=reminder_id,
        content=payload.content,
        due_at=payload.due_at,
        recurrence=payload.recurrence,
        expected_version=payload.expected_version,
    )
    result = await container.reminders(uow).update.execute(command)
    return ReminderResponse.model_validate(result)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: UUID,
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> None:
    await container.reminders(uow).delete.execute(user_id, reminder_id)


@router.post("/{reminder_id}/snooze", response_model=ReminderResponse)
async def snooze_reminder(
    reminder_id: UUID,
    payload: SnoozeRequest,
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> ReminderResponse:
    command = SnoozeReminderCommand(
        user_id=user_id,
        reminder_id=reminder_id,
        snooze_until=payload.snooze_until,
        expected_version=payload.expected_version,
    )
    result = await container.reminders(uow).snooze.execute(command)
    return ReminderResponse.model_validate(result)


@router.post("/{reminder_id}/done", response_model=ReminderResponse)
async def done_reminder(
    reminder_id: UUID,
    user_id: UUID = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
    container: Container = Depends(get_container),
) -> ReminderResponse:
    result = await container.reminders(uow).done.execute(user_id, reminder_id)
    return ReminderResponse.model_validate(result)
