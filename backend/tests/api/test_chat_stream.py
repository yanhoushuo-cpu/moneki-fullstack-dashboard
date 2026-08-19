from __future__ import annotations

import asyncio
import json

from app.ai import streaming
from app.ai.models import ChatResponse


def _events(body: str) -> list[tuple[str, dict]]:
    parsed: list[tuple[str, dict]] = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        name = next(line[7:] for line in lines if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        parsed.append((name, data))
    return parsed


def _without_generated_at(response: dict) -> dict:
    normalized = {**response}
    normalized["evidence"] = [
        {key: value for key, value in evidence.items() if key != "generated_at"}
        for evidence in response["evidence"]
    ]
    return normalized


def test_chat_stream_emits_deltas_and_same_structured_result(api_client):
    request = {"message": "牛肉poke 五月卖了多少钱？", "history": []}
    expected = api_client.post("/api/v1/chat", json=request).json()

    with api_client.stream("POST", "/api/v1/chat/stream", json=request) as response:
        body = "".join(response.iter_text())
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"

    events = _events(body)
    names = [name for name, _ in events]
    assert names[:2] == ["start", "status"]
    assert names[-2:] == ["result", "done"]
    assert "".join(data["text"] for name, data in events if name == "delta") == expected["answer"]
    result = next(data["response"] for name, data in events if name == "result")
    assert _without_generated_at(result) == _without_generated_at(expected)


def test_chat_stream_preserves_unsupported_boundary(api_client):
    with api_client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"message": "明天北京会下雨吗？", "history": []},
    ) as response:
        events = _events("".join(response.iter_text()))

    result = next(data["response"] for name, data in events if name == "result")
    assert result["status"] == "unsupported"
    assert result["evidence"] == []


def test_chat_stream_validates_input_before_starting_stream(api_client):
    response = api_client.post("/api/v1/chat/stream", json={"message": "", "history": []})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")


def test_stream_generator_converts_late_failure_to_error_event(monkeypatch):
    response = ChatResponse(answer="可信回答", status="answered", mode="mock")

    def fail_to_split(_answer: str, _max_chars: int = 12) -> list[str]:
        raise RuntimeError("stream failed")

    monkeypatch.setattr(streaming, "split_answer", fail_to_split)

    async def collect() -> str:
        return "".join(
            [frame async for frame in streaming.stream_chat_response(response, delay_seconds=0)]
        )

    events = _events(asyncio.run(collect()))

    assert [name for name, _ in events] == ["start", "status", "error"]
    assert events[-1][1] == {"message": "流式传输中断，请重试。"}
