from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas import ProviderEvent, ProviderRequest


class Provider(ABC):
    """Provider-independent interface used by the council orchestrator."""

    name: str

    @abstractmethod
    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        """Stream normalized provider events."""
        raise NotImplementedError

    async def health(self) -> bool:
        return True
