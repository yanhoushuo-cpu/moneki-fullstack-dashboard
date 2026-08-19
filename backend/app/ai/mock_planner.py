from __future__ import annotations

import calendar
from datetime import date

from app.ai.models import ChatRequest, PlanDecision, ToolCall
from app.analytics.models import MetaResult


MONTHS = {
    "一月": 1,
    "二月": 2,
    "三月": 3,
    "四月": 4,
    "五月": 5,
    "六月": 6,
    "七月": 7,
    "八月": 8,
    "九月": 9,
    "十月": 10,
    "十一月": 11,
    "十二月": 12,
}


def _month_range(year: int, month: int) -> tuple[str, str]:
    return (
        date(year, month, 1).isoformat(),
        date(year, month, calendar.monthrange(year, month)[1]).isoformat(),
    )


def _previous_month(value: date) -> date:
    return date(value.year - 1, 12, 1) if value.month == 1 else date(value.year, value.month - 1, 1)


class MockPlanner:
    mode = "mock"

    def __init__(self, meta: MetaResult):
        self.meta = meta

    def _find_month(self, text: str) -> int | None:
        return next((number for label, number in MONTHS.items() if label in text), None)

    def _find_product(self, text: str) -> str | None:
        ordered = sorted(self.meta.products, key=lambda product: len(product.product_name), reverse=True)
        return next((product.product_name for product in ordered if product.product_name in text), None)

    def plan(self, request: ChatRequest) -> PlanDecision:
        context = " ".join(message.content for message in request.history)
        current = request.message.strip()
        combined = f"{context} {current}"
        if not self.meta.date_min or not self.meta.date_max:
            return PlanDecision(unsupported_reason="当前数据库没有可查询的销售日期。")

        if "数据质量" in current or "脏数据" in current:
            return PlanDecision(tool_call=ToolCall(name="get_data_quality", arguments={}))

        if "客单价" in current and any(word in current for word in ("涨", "跌", "趋势", "最近")):
            latest = date.fromisoformat(self.meta.date_max)
            current_start, current_end = _month_range(latest.year, latest.month)
            previous = _previous_month(latest)
            previous_start, previous_end = _month_range(previous.year, previous.month)
            return PlanDecision(
                tool_call=ToolCall(
                    name="compare_periods",
                    arguments={
                        "metric": "average_order_value",
                        "current_start": current_start,
                        "current_end": current_end,
                        "previous_start": previous_start,
                        "previous_end": previous_end,
                        "filters": {},
                    },
                )
            )

        if "品类" in current and any(word in current for word in ("最高", "最多", "第一", "哪个")):
            return PlanDecision(
                tool_call=ToolCall(
                    name="get_top_entities",
                    arguments={
                        "dimension": "store_category" if "门店" in current else "product_category",
                        "metric": "revenue",
                        "start_date": self.meta.date_min,
                        "end_date": self.meta.date_max,
                        "limit": 1,
                    },
                )
            )

        product_name = self._find_product(combined)
        month = self._find_month(current) or self._find_month(context)
        is_metric_question = any(word in current for word in ("多少", "营业额", "卖了", "销售"))
        is_month_follow_up = month is not None and "呢" in current and bool(request.history)
        if product_name and (is_metric_question or is_month_follow_up):
            if month:
                start_date, end_date = _month_range(2026, month)
            else:
                start_date, end_date = self.meta.date_min, self.meta.date_max
            return PlanDecision(
                tool_call=ToolCall(
                    name="get_revenue",
                    arguments={
                        "start_date": start_date,
                        "end_date": end_date,
                        "product_name": product_name,
                    },
                )
            )

        return PlanDecision(unsupported_reason="这个问题超出了当前销售数据可以回答的范围。")
