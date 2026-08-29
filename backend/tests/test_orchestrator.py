import asyncio

import pytest

from app.orchestrator import Council
from app.providers.base import Provider
from app.schemas import EventType, ProviderEvent, ProviderRequest


class FakeProvider(Provider):
    def __init__(self, name: str, events: list[ProviderEvent], delay: float = 0.0):
        self.name = name
        self.events = events
        self.delay = delay
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()
        self.completed = asyncio.Event()

    async def stream(self, request: ProviderRequest):
        self.started.set()
        try:
            for event in self.events:
                if self.delay:
                    await asyncio.sleep(self.delay)
                yield event
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        finally:
            self.completed.set()


@pytest.mark.asyncio
async def test_council_streams_provider_events_before_provider_finishes():
    provider = FakeProvider(
        "slow",
        [
            ProviderEvent(EventType.MODEL_DELTA, "slow", "demo", text="first"),
            ProviderEvent(EventType.MODEL_DELTA, "slow", "demo", text="second"),
        ],
        delay=0.05,
    )
    council = Council([provider])
    request = ProviderRequest("demo", [{"role": "user", "content": "hi"}])

    stream = council.ask(request)
    first = await stream.__anext__()
    assert first.type is EventType.REQUEST_STARTED

    first_delta = await stream.__anext__()
    assert first_delta.type is EventType.MODEL_STARTED
    second_delta = await stream.__anext__()
    assert second_delta.text == "first"
    assert not provider.completed.is_set()

    await stream.aclose()
    assert provider.cancelled.is_set()
    assert provider.completed.is_set()


@pytest.mark.asyncio
async def test_council_cancels_all_providers_when_consumer_closes():
    providers = [
        FakeProvider(
            f"p{i}",
            [ProviderEvent(EventType.MODEL_DELTA, f"p{i}", "demo", text="x")],
            delay=10,
        )
        for i in range(3)
    ]
    council = Council(providers)
    request = ProviderRequest("demo", [{"role": "user", "content": "hi"}])

    stream = council.ask(request)
    await stream.__anext__()
    await asyncio.wait_for(
        asyncio.gather(*(provider.started.wait() for provider in providers)), 1
    )
    await stream.aclose()

    await asyncio.wait_for(
        asyncio.gather(*(provider.completed.wait() for provider in providers)), 1
    )
    assert all(provider.cancelled.is_set() for provider in providers)


@pytest.mark.asyncio
async def test_one_provider_error_does_not_stop_other_provider():
    class BrokenProvider(Provider):
        name = "broken"

        async def stream(self, request):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    healthy = FakeProvider(
        "healthy",
        [ProviderEvent(EventType.MODEL_DELTA, "healthy", "demo", text="ok")],
    )
    council = Council([BrokenProvider(), healthy])
    request = ProviderRequest("demo", [{"role": "user", "content": "hi"}])

    events = [event async for event in council.ask(request)]
    assert any(e.type is EventType.MODEL_ERROR and e.provider == "broken" for e in events)
    assert any(e.type is EventType.MODEL_DELTA and e.text == "ok" for e in events)
    assert events[-1].type is EventType.REQUEST_COMPLETED
