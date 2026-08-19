from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatMessage(AiModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(AiModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)


class ToolCall(AiModel):
    name: str
    arguments: dict[str, Any]


class PlanDecision(AiModel):
    tool_call: ToolCall | None = None
    unsupported_reason: str | None = None


class Evidence(AiModel):
    tool: str
    parameters: dict[str, Any]
    result: dict[str, Any]
    ingestion_run_id: int
    generated_at: str


class DashboardAction(AiModel):
    start_date: str
    end_date: str
    store_id: str | None = None
    highlight_product: str | None = None


class ChatResponse(AiModel):
    answer: str
    status: Literal["answered", "unsupported", "unavailable"]
    mode: Literal["mock", "provider"]
    evidence: list[Evidence] = Field(default_factory=list)
    dashboard_action: DashboardAction | None = None
    suggestions: list[str] = Field(default_factory=list)

