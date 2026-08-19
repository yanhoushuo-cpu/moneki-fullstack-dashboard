from __future__ import annotations

from typing import Protocol

from app.ai.models import (
    ChatRequest,
    ChatResponse,
    DashboardAction,
    Evidence,
    PlanDecision,
)
from app.ai.tools import ToolExecutor
from app.analytics.service import AnalyticsService


SUGGESTIONS = [
    "哪个品类的门店营业额最高？",
    "牛肉poke 六月卖了多少钱？",
    "客单价最近是涨了还是跌了？",
    "这批数据有哪些质量问题？",
]


class Planner(Protocol):
    mode: str

    def plan(self, request: ChatRequest) -> PlanDecision: ...


def _format_money(cents: int | None) -> str:
    return "暂无数据" if cents is None else f"¥{cents / 100:,.2f}"


class ChatService:
    def __init__(self, *, analytics: AnalyticsService, planner: Planner):
        self.analytics = analytics
        self.planner = planner
        self.executor = ToolExecutor(analytics)

    def answer(self, request: ChatRequest) -> ChatResponse:
        try:
            decision = self.planner.plan(request)
            if decision.tool_call is None:
                return ChatResponse(
                    answer=decision.unsupported_reason or "当前数据无法回答这个问题。",
                    status="unsupported",
                    mode=self.planner.mode,
                    suggestions=SUGGESTIONS,
                )
            evidence = self.executor.execute(decision.tool_call)
            answer = self._answer_from_evidence(evidence)
            return ChatResponse(
                answer=answer,
                status="answered",
                mode=self.planner.mode,
                evidence=[evidence],
                dashboard_action=self._dashboard_action(evidence),
                suggestions=SUGGESTIONS[:3],
            )
        except Exception:
            return ChatResponse(
                answer="查询暂时不可用。看板仍可正常使用，请稍后重试。",
                status="unavailable",
                mode=self.planner.mode,
                suggestions=SUGGESTIONS[:3],
            )

    @staticmethod
    def _answer_from_evidence(evidence: Evidence) -> str:
        result = evidence.result
        parameters = evidence.parameters
        if evidence.tool == "get_revenue":
            subject = parameters.get("product_name") or parameters.get("store_category") or "所选范围"
            return (
                f"{subject}在 {parameters['start_date']} 至 {parameters['end_date']} 的营业额为 "
                f"{_format_money(result['revenue_cents'])}，覆盖 {result['order_count']:,} 个订单。"
            )
        if evidence.tool == "get_top_entities":
            items = result.get("items", [])
            if not items:
                return "所选范围内没有可排名的数据。"
            leader = items[0]
            return f"营业额最高的是“{leader['name']}”，营业额为 {_format_money(leader['value_cents'])}。"
        if evidence.tool == "compare_periods":
            words = {"up": "上涨", "down": "下降", "flat": "持平"}
            direction = words.get(result["direction"], "持平")
            change = result.get("change_percent")
            suffix = "，缺少可用基线" if change is None else f" {abs(change):.1f}%"
            return (
                f"最近一个完整月的客单价为 {_format_money(result['current_value'])}，"
                f"相比上月{direction}{suffix}。"
            )
        if evidence.tool == "get_trend":
            return f"已查询 {len(result.get('points', []))} 个日度数据点，可在趋势图中查看。"
        if evidence.tool == "get_data_quality":
            summary = result.get("summary", {})
            return (
                f"原始数据 {summary.get('raw_sales', 0):,} 行，清洗后有效 "
                f"{summary.get('valid_sales', 0):,} 行，隔离 {summary.get('quarantined_sales', 0):,} 行。"
            )
        return "查询完成，数据依据已附在回答下方。"

    @staticmethod
    def _dashboard_action(evidence: Evidence) -> DashboardAction | None:
        parameters = evidence.parameters
        if evidence.tool in {"get_revenue", "get_top_entities", "get_trend"}:
            return DashboardAction(
                start_date=parameters["start_date"],
                end_date=parameters["end_date"],
                store_id=parameters.get("store_id"),
                highlight_product=parameters.get("product_name"),
            )
        if evidence.tool == "compare_periods":
            return DashboardAction(
                start_date=parameters["current_start"],
                end_date=parameters["current_end"],
                store_id=parameters.get("store_id"),
            )
        return None
