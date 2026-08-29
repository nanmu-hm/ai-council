from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.providers.base import Provider
from app.schemas import EventType, ProviderEvent, ProviderRequest


class OpenAICompatibleProvider(Provider):
    """Adapter for OpenAI-compatible chat-completions gateways.

    This deliberately knows nothing about upstream provider internals. WebModel,
    Ollama and other compatible gateways can be configured through base_url.
    """

    def __init__(self, name: str, base_url: str, api_key: str = "", timeout: float = 120.0):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": request.model,
            "messages": request.messages,
            "stream": True,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        for choice in chunk.get("choices", []):
                            delta = choice.get("delta", {}) or {}
                            text = delta.get("content") or ""
                            if text:
                                yield ProviderEvent(
                                    EventType.MODEL_DELTA,
                                    self.name,
                                    request.model,
                                    text=text,
                                )
            yield ProviderEvent(EventType.MODEL_COMPLETED, self.name, request.model)
        except Exception as exc:
            yield ProviderEvent(
                EventType.MODEL_ERROR,
                self.name,
                request.model,
                error=str(exc),
            )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/models")
                return response.is_success
        except httpx.HTTPError:
            return False
