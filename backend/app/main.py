from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.orchestrator import Council
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import ProviderRequest

app = FastAPI(title="AI Council", version="0.1.0")

webmodel_url = os.getenv("WEBMODEL_BASE_URL", "http://webmodel:8000/v1")
webmodel_key = os.getenv("WEBMODEL_API_KEY", "")
ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

council = Council([
    OpenAICompatibleProvider("webmodel", webmodel_url, webmodel_key),
    OpenAICompatibleProvider("ollama", ollama_url),
])


class AskRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[dict[str, str]] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/council/stream")
async def council_stream(body: AskRequest) -> StreamingResponse:
    request = ProviderRequest(
        model=body.model,
        messages=body.messages,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    async def events() -> AsyncIterator[str]:
        async for event in council.ask(request):
            payload = {
                "type": event.type.value,
                "provider": event.provider,
                "model": event.model,
                "text": event.text,
                "error": event.error,
                "metadata": event.metadata or {},
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
