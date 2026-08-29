from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(str, Enum):
    REQUEST_STARTED = "request.started"
    MODEL_STARTED = "model.started"
    MODEL_DELTA = "model.delta"
    MODEL_COMPLETED = "model.completed"
    MODEL_ERROR = "model.error"
    REQUEST_COMPLETED = "request.completed"


@dataclass(slots=True)
class ProviderRequest:
    model: str
    messages: list[dict[str, str]]
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(slots=True)
class ProviderEvent:
    type: EventType
    provider: str
    model: str
    text: str = ""
    error: str | None = None
    metadata: dict[str, Any] | None = None
