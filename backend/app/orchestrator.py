from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from app.providers.base import Provider
from app.schemas import EventType, ProviderEvent, ProviderRequest


_SENTINEL = object()


class Council:
    def __init__(self, providers: list[Provider], max_concurrency: int = 8):
        self.providers = providers
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(
        self,
        provider: Provider,
        request: ProviderRequest,
        queue: asyncio.Queue[ProviderEvent | object],
    ) -> None:
        async with self.semaphore:
            await queue.put(ProviderEvent(EventType.MODEL_STARTED, provider.name, request.model))
            try:
                async for event in provider.stream(request):
                    await queue.put(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await queue.put(
                    ProviderEvent(
                        EventType.MODEL_ERROR,
                        provider.name,
                        request.model,
                        error=str(exc),
                    )
                )
            finally:
                await queue.put(_SENTINEL)

    async def ask(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        request_id = str(uuid.uuid4())
        yield ProviderEvent(
            EventType.REQUEST_STARTED,
            "council",
            request.model,
            metadata={"request_id": request_id},
        )

        queue: asyncio.Queue[ProviderEvent | object] = asyncio.Queue()
        tasks = [
            asyncio.create_task(self._run(provider, request, queue))
            for provider in self.providers
        ]
        completed = 0

        try:
            while completed < len(tasks):
                item = await queue.get()
                if item is _SENTINEL:
                    completed += 1
                    continue
                item.metadata = {**(item.metadata or {}), "request_id": request_id}
                yield item

            yield ProviderEvent(
                EventType.REQUEST_COMPLETED,
                "council",
                request.model,
                metadata={"request_id": request_id},
            )
        finally:
            # The SSE consumer may disconnect at any await/yield point.  Never
            # leave provider tasks running after the council stream is gone.
            pending = [task for task in tasks if not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            # Also retrieve already-finished exceptions so they cannot become
            # "Task exception was never retrieved" warnings.
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
