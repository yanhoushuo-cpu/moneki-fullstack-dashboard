from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MoneyResponse(ApiModel):
    cents: int
    formatted: str


class FiltersResponse(ApiModel):
    start_date: str
    end_date: str
    store_id: str | None


class SummaryResponse(ApiModel):
    revenue: MoneyResponse
    order_count: int
    average_order_value: MoneyResponse | None
    previous_revenue: MoneyResponse
    previous_order_count: int
    previous_average_order_value: MoneyResponse | None
    revenue_change_percent: float | None
    order_change_percent: float | None
    average_order_value_change_percent: float | None


class DailyResponse(ApiModel):
    date: str
    revenue: MoneyResponse
    order_count: int
    average_order_value: MoneyResponse | None


class TopProductResponse(ApiModel):
    product_id: str
    product_name: str
    product_category: str
    quantity: int
    revenue: MoneyResponse
    order_count: int


class StoreComparisonResponse(ApiModel):
    store_id: str
    store_name: str
    category: str
    district: str
    revenue: MoneyResponse
    order_count: int
    share_percent: float


class CoverageResponse(ApiModel):
    valid_rows: int
    date_min: str | None
    date_max: str | None
    ingestion_run_id: int
    updated_at: str


class DashboardResponse(ApiModel):
    filters: FiltersResponse
    summary: SummaryResponse
    daily: list[DailyResponse]
    top_products: list[TopProductResponse]
    store_comparison: list[StoreComparisonResponse]
    coverage: CoverageResponse


class DateRangeResponse(ApiModel):
    min: str | None
    max: str | None


class StoreOptionResponse(ApiModel):
    store_id: str
    store_name: str
    category: str
    district: str


class MetaResponse(ApiModel):
    date_range: DateRangeResponse
    stores: list[StoreOptionResponse]
    ingestion_run_id: int
    presets: list[dict[str, str]]


class HealthResponse(ApiModel):
    status: str
    database: str
    ingestion_run_id: int


class QualityRuleResponse(ApiModel):
    code: str
    label: str
    action: str


class DataQualityResponse(ApiModel):
    ingestion_run_id: int
    source_hash: str
    rule_version: str
    updated_at: str
    summary: dict[str, Any]
    rules: list[QualityRuleResponse]


def money(cents: int | None) -> MoneyResponse | None:
    if cents is None:
        return None
    return MoneyResponse(cents=cents, formatted=f"¥{cents / 100:,.2f}")

