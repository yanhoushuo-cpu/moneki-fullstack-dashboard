from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.models import ChatRequest, PlanDecision, ToolCall
from app.ai.tools import TOOL_SCHEMAS


class ProviderPlanner:
    mode = "provider"

    def __init__(self, *, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def plan(self, request: ChatRequest) -> PlanDecision:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "你是餐饮经营数据查询规划器。数值问题必须选择一个提供的工具；"
                    "无法由工具回答时不要猜测。"
                ),
            },
            *[message.model_dump() for message in request.history],
            {"role": "user", "content": request.message},
        ]
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "tools": TOOL_SCHEMAS,
                "tool_choice": "auto",
                "temperature": 0,
            },
            timeout=20,
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if not calls:
            return PlanDecision(unsupported_reason="模型未找到可信的数据查询路径。")
        function = calls[0]["function"]
        return PlanDecision(
            tool_call=ToolCall(
                name=function["name"],
                arguments=json.loads(function["arguments"]),
            )
        )

