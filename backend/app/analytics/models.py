from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class DashboardFilters:
    start_date: date
    end_date: date
    store_id: str | None = None

    def validate(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")

    def previous_period(self) -> tuple[date, date]:
        self.validate()
        inclusive_days = (self.end_date - self.start_date).days + 1
        previous_end = self.start_date - timedelta(days=1)
        return previous_end - timedelta(days=inclusive_days - 1), previous_end


@dataclass(frozen=True)
class MetricSummary:
    revenue_cents: int
    order_count: int
    average_order_value_cents: int | None
    previous_revenue_cents: int
    previous_order_count: int
    previous_average_order_value_cents: int | None
    revenue_change_percent: float | None
    order_change_percent: float | None
    average_order_value_change_percent: float | None


@dataclass(frozen=True)
class DailyPoint:
    date: str
    revenue_cents: int
    order_count: int
    average_order_value_cents: int | None


@dataclass(frozen=True)
class TopProduct:
    product_id: str
    product_name: str
    product_category: str
    quantity: int
    revenue_cents: int
    order_count: int


@dataclass(frozen=True)
class StoreComparison:
    store_id: str
    store_name: str
    category: str
    district: str
    revenue_cents: int
    order_count: int
    share_percent: float


@dataclass(frozen=True)
class Coverage:
    valid_rows: int
    date_min: str | None
    date_max: str | None
    ingestion_run_id: int
    updated_at: str


@dataclass(frozen=True)
class DashboardResult:
    filters: DashboardFilters
    summary: MetricSummary
    daily: list[DailyPoint]
    top_products: list[TopProduct]
    store_comparison: list[StoreComparison]
    coverage: Coverage


@dataclass(frozen=True)
class RevenueResult:
    revenue_cents: int
    order_count: int
    average_order_value_cents: int | None
    parameters: dict[str, Any]


@dataclass(frozen=True)
class TopEntity:
    name: str
    value_cents: int
    order_count: int


@dataclass(frozen=True)
class TopEntitiesResult:
    dimension: str
    metric: str
    items: list[TopEntity]
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ComparisonResult:
    metric: str
    current_value: int | None
    previous_value: int | None
    change_percent: float | None
    direction: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class TrendPoint:
    date: str
    value: int | None


@dataclass(frozen=True)
class TrendResult:
    metric: str
    points: list[TrendPoint]
    parameters: dict[str, Any]


@dataclass(frozen=True)
class DataQualityResult:
    ingestion_run_id: int
    source_hash: str
    rule_version: str
    updated_at: str
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StoreOption:
    store_id: str
    store_name: str
    category: str
    district: str


@dataclass(frozen=True)
class MetaResult:
    date_min: str | None
    date_max: str | None
    stores: list[StoreOption]
    ingestion_run_id: int

