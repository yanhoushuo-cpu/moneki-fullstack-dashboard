from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from app.ai.models import ChatResponse


def split_answer(answer: str, max_chars: int = 12) -> list[str]:
    chunks: list[str] = []
    current = ""
    for character in answer:
        current += character
        if len(current) >= max_chars or character in "，。！？；":
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks


def encode_sse(event: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


async def stream_chat_response(
    response: ChatResponse,
    delay_seconds: float = 0.015,
) -> AsyncIterator[str]:
    yield encode_sse("start", {})
    yield encode_sse("status", {"message": "正在查询可信经营数据…"})
    try:
        for chunk in split_answer(response.answer):
            yield encode_sse("delta", {"text": chunk})
            if delay_seconds:
                await asyncio.sleep(delay_seconds)
        yield encode_sse("result", {"response": response.model_dump(mode="json")})
        yield encode_sse("done", {})
    except Exception:
        yield encode_sse("error", {"message": "流式传输中断，请重试。"})
