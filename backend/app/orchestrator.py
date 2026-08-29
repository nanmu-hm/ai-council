from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from app.providers.base import Provider
from app.schemas import EventType, ProviderEvent, ProviderRequest


class Council:
    def __init__(self, providers: list[Provider], max_concurrency: int = 8):
        self.providers = providers
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(self, provider: Provider, request: ProviderRequest) -> list[ProviderEvent]:
        async with self.semaphore:
            events = [ProviderEvent(EventType.MODEL_STARTED, provider.name, request.model)]
            async for event in provider.stream(request):
                events.append(event)
            return events

    async def ask(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        request_id = str(uuid.uuid4())
        yield ProviderEvent(EventType.REQUEST_STARTED, "council", request.model, metadata={"request_id": request_id})

        tasks = [asyncio.create_task(self._run(provider, request)) for provider in self.providers]
        for task in asyncio.as_completed(tasks):
            try:
                for event in await task:
                    event.metadata = {**(event.metadata or {}), "request_id": request_id}
                    yield event
            except Exception as exc:
                yield ProviderEvent(EventType.MODEL_ERROR, "council", request.model, error=str(exc), metadata={"request_id": request_id})

        yield ProviderEvent(EventType.REQUEST_COMPLETED, "council", request.model, metadata={"request_id": request_id})
