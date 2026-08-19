from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ai.models import Evidence, ToolCall
from app.analytics.service import AnalyticsService


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RevenueArguments(ToolArguments):
    start_date: date
    end_date: date
    product_name: str | None = None
    store_id: str | None = None
    store_category: str | None = None


class TopEntitiesArguments(ToolArguments):
    dimension: Literal["store_category", "store", "product", "product_category"]
    metric: Literal["revenue"] = "revenue"
    start_date: date
    end_date: date
    limit: int = Field(default=10, ge=1, le=20)


class ComparePeriodsArguments(ToolArguments):
    metric: Literal["revenue", "order_count", "average_order_value"]
    current_start: date
    current_end: date
    previous_start: date
    previous_end: date
    filters: dict[str, str] = Field(default_factory=dict)


class TrendArguments(ToolArguments):
    metric: Literal["revenue", "order_count", "average_order_value"]
    start_date: date
    end_date: date
    granularity: Literal["day"] = "day"
    filters: dict[str, str] = Field(default_factory=dict)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_revenue",
            "description": "查询日期区间内的营业额、订单数和客单价，可按商品、门店或门店品类过滤。",
            "parameters": RevenueArguments.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_entities",
            "description": "按营业额查询排名最高的门店、门店品类、商品或商品品类。",
            "parameters": TopEntitiesArguments.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": "比较两个日期区间的营业额、订单数或客单价。",
            "parameters": ComparePeriodsArguments.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend",
            "description": "查询指标的每日趋势。",
            "parameters": TrendArguments.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality",
            "description": "查询当前数据导入与清洗质量。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


class ToolExecutor:
    def __init__(self, analytics: AnalyticsService):
        self.analytics = analytics

    def execute(self, call: ToolCall) -> Evidence:
        if call.name == "get_revenue":
            arguments = RevenueArguments.model_validate(call.arguments)
            result = self.analytics.get_revenue(**arguments.model_dump())
        elif call.name == "get_top_entities":
            arguments = TopEntitiesArguments.model_validate(call.arguments)
            result = self.analytics.get_top_entities(**arguments.model_dump())
        elif call.name == "compare_periods":
            arguments = ComparePeriodsArguments.model_validate(call.arguments)
            result = self.analytics.compare_periods(**arguments.model_dump())
        elif call.name == "get_trend":
            arguments = TrendArguments.model_validate(call.arguments)
            result = self.analytics.get_trend(**arguments.model_dump())
        elif call.name == "get_data_quality":
            if call.arguments:
                raise ValueError("get_data_quality does not accept arguments")
            arguments = None
            result = self.analytics.get_data_quality()
        else:
            raise ValueError(f"unsupported tool: {call.name}")

        quality = self.analytics.get_data_quality()
        parameters = arguments.model_dump(mode="json") if arguments else {}
        return Evidence(
            tool=call.name,
            parameters=parameters,
            result=asdict(result),
            ingestion_run_id=quality.ingestion_run_id,
            generated_at=datetime.now(UTC).isoformat(),
        )

