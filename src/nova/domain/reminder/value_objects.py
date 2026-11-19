from dataclasses import dataclass
from datetime import datetime

from nova.domain.shared.errors import ValidationError
from nova.domain.shared.ids import as_utc


@dataclass(frozen=True, slots=True)
class ReminderContent:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value or len(value) > 500:
            raise ValidationError("reminder content must be 1-500 characters")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class DueAt:
    value: datetime

    def __post_init__(self) -> None:
        try:
            value = as_utc(self.value)
        except ValueError as exc:
            raise ValidationError("due_at must be timezone-aware") from exc
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class RecurrenceRule:
    value: str | None = None

    def __post_init__(self) -> None:
        if self.value is not None and (not self.value.strip() or len(self.value) > 255):
            raise ValidationError("recurrence must be 1-255 characters or null")
