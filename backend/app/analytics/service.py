from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from sqlalchemy import Engine, text

from app.analytics.models import (
    ComparisonResult,
    Coverage,
    DailyPoint,
    DashboardFilters,
    DashboardResult,
    DataQualityResult,
    MetaResult,
    MetricSummary,
    RevenueResult,
    StoreComparison,
    StoreOption,
    TopEntitiesResult,
    TopEntity,
    TopProduct,
    TrendPoint,
    TrendResult,
)


def _average(revenue_cents: int, order_count: int) -> int | None:
    if order_count == 0:
        return None
    return int(
        (Decimal(revenue_cents) / Decimal(order_count)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def _change(current: int | None, previous: int | None) -> float | None:
    if current is None or previous in {None, 0}:
        return None
    value = ((Decimal(current) - Decimal(previous)) / Decimal(previous)) * 100
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


class AnalyticsService:
    def __init__(self, engine: Engine):
        self.engine = engine

    @staticmethod
    def _where(
        start_date: date,
        end_date: date,
        *,
        store_id: str | None = None,
        product_name: str | None = None,
        store_category: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        clauses = ["s.date BETWEEN :start_date AND :end_date"]
        parameters: dict[str, Any] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        if store_id:
            clauses.append("s.store_id = :store_id")
            parameters["store_id"] = store_id.strip().upper()
        if product_name:
            clauses.append("p.product_name = :product_name")
            parameters["product_name"] = product_name.strip()
        if store_category:
            clauses.append("st.category = :store_category")
            parameters["store_category"] = store_category.strip()
        return " AND ".join(clauses), parameters

    def _metrics(
        self,
        start_date: date,
        end_date: date,
        *,
        store_id: str | None = None,
        product_name: str | None = None,
        store_category: str | None = None,
    ) -> tuple[int, int, int | None]:
        where, parameters = self._where(
            start_date,
            end_date,
            store_id=store_id,
            product_name=product_name,
            store_category=store_category,
        )
        statement = text(
            f"""
            SELECT COALESCE(SUM(s.amount_cents), 0) AS revenue_cents,
                   COUNT(DISTINCT s.order_id) AS order_count
            FROM sales s
            JOIN products p ON p.product_id = s.product_id
            JOIN stores st ON st.store_id = s.store_id
            WHERE {where}
            """
        )
        with self.engine.connect() as connection:
            row = connection.execute(statement, parameters).mappings().one()
        revenue = int(row["revenue_cents"])
        orders = int(row["order_count"])
        return revenue, orders, _average(revenue, orders)

    def get_dashboard(self, filters: DashboardFilters) -> DashboardResult:
        filters.validate()
        revenue, orders, aov = self._metrics(
            filters.start_date, filters.end_date, store_id=filters.store_id
        )
        previous_start, previous_end = filters.previous_period()
        previous_revenue, previous_orders, previous_aov = self._metrics(
            previous_start, previous_end, store_id=filters.store_id
        )
        where, parameters = self._where(
            filters.start_date, filters.end_date, store_id=filters.store_id
        )

        with self.engine.connect() as connection:
            daily_rows = connection.execute(
                text(
                    f"""
                    SELECT s.date,
                           SUM(s.amount_cents) AS revenue_cents,
                           COUNT(DISTINCT s.order_id) AS order_count
                    FROM sales s
                    JOIN products p ON p.product_id = s.product_id
                    JOIN stores st ON st.store_id = s.store_id
                    WHERE {where}
                    GROUP BY s.date
                    ORDER BY s.date
                    """
                ),
                parameters,
            ).mappings().all()
            product_rows = connection.execute(
                text(
                    f"""
                    SELECT p.product_id, p.product_name, p.product_category,
                           SUM(s.qty) AS quantity,
                           SUM(s.amount_cents) AS revenue_cents,
                           COUNT(DISTINCT s.order_id) AS order_count
                    FROM sales s
                    JOIN products p ON p.product_id = s.product_id
                    JOIN stores st ON st.store_id = s.store_id
                    WHERE {where}
                    GROUP BY p.product_id, p.product_name, p.product_category
                    ORDER BY revenue_cents DESC, p.product_id ASC
                    LIMIT 10
                    """
                ),
                parameters,
            ).mappings().all()
            store_rows = connection.execute(
                text(
                    f"""
                    SELECT st.store_id, st.store_name, st.category, st.district,
                           SUM(s.amount_cents) AS revenue_cents,
                           COUNT(DISTINCT s.order_id) AS order_count
                    FROM sales s
                    JOIN products p ON p.product_id = s.product_id
                    JOIN stores st ON st.store_id = s.store_id
                    WHERE {where}
                    GROUP BY st.store_id, st.store_name, st.category, st.district
                    ORDER BY revenue_cents DESC, st.store_id ASC
                    """
                ),
                parameters,
            ).mappings().all()
            run = connection.execute(
                text(
                    """
                    SELECT id, completed_at FROM ingestion_runs
                    ORDER BY id DESC LIMIT 1
                    """
                )
            ).mappings().one()
            coverage_row = connection.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS valid_rows, MIN(s.date) AS date_min, MAX(s.date) AS date_max
                    FROM sales s
                    JOIN products p ON p.product_id = s.product_id
                    JOIN stores st ON st.store_id = s.store_id
                    WHERE {where}
                    """
                ),
                parameters,
            ).mappings().one()

        daily = [
            DailyPoint(
                date=str(row["date"]),
                revenue_cents=int(row["revenue_cents"]),
                order_count=int(row["order_count"]),
                average_order_value_cents=_average(
                    int(row["revenue_cents"]), int(row["order_count"])
                ),
            )
            for row in daily_rows
        ]
        top_products = [
            TopProduct(
                product_id=str(row["product_id"]),
                product_name=str(row["product_name"]),
                product_category=str(row["product_category"]),
                quantity=int(row["quantity"]),
                revenue_cents=int(row["revenue_cents"]),
                order_count=int(row["order_count"]),
            )
            for row in product_rows
        ]
        store_comparison = [
            StoreComparison(
                store_id=str(row["store_id"]),
                store_name=str(row["store_name"]),
                category=str(row["category"]),
                district=str(row["district"]),
                revenue_cents=int(row["revenue_cents"]),
                order_count=int(row["order_count"]),
                share_percent=round(int(row["revenue_cents"]) / revenue * 100, 1)
                if revenue
                else 0.0,
            )
            for row in store_rows
        ]
        summary = MetricSummary(
            revenue_cents=revenue,
            order_count=orders,
            average_order_value_cents=aov,
            previous_revenue_cents=previous_revenue,
            previous_order_count=previous_orders,
            previous_average_order_value_cents=previous_aov,
            revenue_change_percent=_change(revenue, previous_revenue),
            order_change_percent=_change(orders, previous_orders),
            average_order_value_change_percent=_change(aov, previous_aov),
        )
        return DashboardResult(
            filters=filters,
            summary=summary,
            daily=daily,
            top_products=top_products,
            store_comparison=store_comparison,
            coverage=Coverage(
                valid_rows=int(coverage_row["valid_rows"]),
                date_min=coverage_row["date_min"],
                date_max=coverage_row["date_max"],
                ingestion_run_id=int(run["id"]),
                updated_at=str(run["completed_at"]),
            ),
        )

    def get_revenue(
        self,
        start_date: date,
        end_date: date,
        product_name: str | None = None,
        store_id: str | None = None,
        store_category: str | None = None,
    ) -> RevenueResult:
        revenue, orders, aov = self._metrics(
            start_date,
            end_date,
            product_name=product_name,
            store_id=store_id,
            store_category=store_category,
        )
        return RevenueResult(
            revenue_cents=revenue,
            order_count=orders,
            average_order_value_cents=aov,
            parameters={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "product_name": product_name,
                "store_id": store_id,
                "store_category": store_category,
            },
        )

    def get_top_entities(
        self,
        dimension: str,
        metric: str,
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> TopEntitiesResult:
        if metric != "revenue":
            raise ValueError("top entity metric must be 'revenue'")
        dimensions = {
            "store_category": "st.category",
            "store": "st.store_name",
            "product": "p.product_name",
            "product_category": "p.product_category",
        }
        if dimension not in dimensions:
            raise ValueError("unsupported top entity dimension")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        where, parameters = self._where(start_date, end_date)
        parameters["limit"] = limit
        expression = dimensions[dimension]
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    SELECT {expression} AS name,
                           SUM(s.amount_cents) AS value_cents,
                           COUNT(DISTINCT s.order_id) AS order_count
                    FROM sales s
                    JOIN products p ON p.product_id = s.product_id
                    JOIN stores st ON st.store_id = s.store_id
                    WHERE {where}
                    GROUP BY {expression}
                    ORDER BY value_cents DESC, name ASC
                    LIMIT :limit
                    """
                ),
                parameters,
            ).mappings().all()
        return TopEntitiesResult(
            dimension=dimension,
            metric=metric,
            items=[
                TopEntity(
                    name=str(row["name"]),
                    value_cents=int(row["value_cents"]),
                    order_count=int(row["order_count"]),
                )
                for row in rows
            ],
            parameters={
                "dimension": dimension,
                "metric": metric,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": limit,
            },
        )

    def compare_periods(
        self,
        metric: str,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
        filters: Mapping[str, str] | None = None,
    ) -> ComparisonResult:
        active_filters = dict(filters or {})
        current = self.get_revenue(
            current_start,
            current_end,
            product_name=active_filters.get("product_name"),
            store_id=active_filters.get("store_id"),
            store_category=active_filters.get("store_category"),
        )
        previous = self.get_revenue(
            previous_start,
            previous_end,
            product_name=active_filters.get("product_name"),
            store_id=active_filters.get("store_id"),
            store_category=active_filters.get("store_category"),
        )
        values = {
            "revenue": (current.revenue_cents, previous.revenue_cents),
            "order_count": (current.order_count, previous.order_count),
            "average_order_value": (
                current.average_order_value_cents,
                previous.average_order_value_cents,
            ),
        }
        if metric not in values:
            raise ValueError("unsupported comparison metric")
        current_value, previous_value = values[metric]
        change = _change(current_value, previous_value)
        direction = "flat"
        if current_value is not None and previous_value is not None:
            direction = "up" if current_value > previous_value else "down" if current_value < previous_value else "flat"
        return ComparisonResult(
            metric=metric,
            current_value=current_value,
            previous_value=previous_value,
            change_percent=change,
            direction=direction,
            parameters={
                "current_start": current_start.isoformat(),
                "current_end": current_end.isoformat(),
                "previous_start": previous_start.isoformat(),
                "previous_end": previous_end.isoformat(),
                **active_filters,
            },
        )

    def get_trend(
        self,
        metric: str,
        start_date: date,
        end_date: date,
        granularity: str = "day",
        filters: Mapping[str, str] | None = None,
    ) -> TrendResult:
        if granularity != "day":
            raise ValueError("only daily granularity is supported")
        active_filters = dict(filters or {})
        where, parameters = self._where(
            start_date,
            end_date,
            store_id=active_filters.get("store_id"),
            product_name=active_filters.get("product_name"),
            store_category=active_filters.get("store_category"),
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    SELECT s.date, SUM(s.amount_cents) AS revenue_cents,
                           COUNT(DISTINCT s.order_id) AS order_count
                    FROM sales s
                    JOIN products p ON p.product_id = s.product_id
                    JOIN stores st ON st.store_id = s.store_id
                    WHERE {where}
                    GROUP BY s.date ORDER BY s.date
                    """
                ),
                parameters,
            ).mappings().all()
        if metric not in {"revenue", "order_count", "average_order_value"}:
            raise ValueError("unsupported trend metric")
        points: list[TrendPoint] = []
        for row in rows:
            revenue = int(row["revenue_cents"])
            orders = int(row["order_count"])
            values = {
                "revenue": revenue,
                "order_count": orders,
                "average_order_value": _average(revenue, orders),
            }
            points.append(TrendPoint(date=str(row["date"]), value=values[metric]))
        return TrendResult(
            metric=metric,
            points=points,
            parameters={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "granularity": granularity,
                **active_filters,
            },
        )

    def get_data_quality(self) -> DataQualityResult:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT id, source_hash, rule_version, completed_at, summary_json
                    FROM ingestion_runs ORDER BY id DESC LIMIT 1
                    """
                )
            ).mappings().one()
        return DataQualityResult(
            ingestion_run_id=int(row["id"]),
            source_hash=str(row["source_hash"]),
            rule_version=str(row["rule_version"]),
            updated_at=str(row["completed_at"]),
            summary=json.loads(row["summary_json"] or "{}"),
        )

    def get_meta(self) -> MetaResult:
        with self.engine.connect() as connection:
            range_row = connection.execute(
                text("SELECT MIN(date) AS date_min, MAX(date) AS date_max FROM sales")
            ).mappings().one()
            stores = connection.execute(
                text(
                    """
                    SELECT store_id, store_name, category, district
                    FROM stores ORDER BY store_id
                    """
                )
            ).mappings().all()
            run_id = connection.execute(
                text("SELECT id FROM ingestion_runs ORDER BY id DESC LIMIT 1")
            ).scalar_one()
        return MetaResult(
            date_min=range_row["date_min"],
            date_max=range_row["date_max"],
            stores=[
                StoreOption(
                    store_id=str(row["store_id"]),
                    store_name=str(row["store_name"]),
                    category=str(row["category"]),
                    district=str(row["district"]),
                )
                for row in stores
            ],
            ingestion_run_id=int(run_id),
        )
