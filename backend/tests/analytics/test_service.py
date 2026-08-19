from __future__ import annotations

import json
from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from app.analytics.models import DashboardFilters
from app.analytics.service import AnalyticsService
from app.db.database import create_engine_for_path
from app.db.schema import IngestionRun, Product, Sale, Store, create_schema


@pytest.fixture()
def service(tmp_path):
    engine = create_engine_for_path(tmp_path / "analytics.db")
    create_schema(engine)
    with Session(engine) as session:
        run = IngestionRun(
            source_hash="a" * 64,
            rule_version="test",
            started_at=datetime(2026, 8, 19, 10, 0),
            completed_at=datetime(2026, 8, 19, 10, 1),
            summary_json=json.dumps({"raw_sales": 5, "valid_sales": 5, "quarantined_sales": 0}),
        )
        session.add(run)
        session.flush()
        session.add_all(
            [
                Store(store_id="S01", store_name="Makai Poke", category="轻食", district="上海·静安"),
                Store(store_id="S02", store_name="Super Souper", category="拉面", district="上海·徐汇"),
                Product(product_id="P01", product_name="牛肉poke", product_category="主食", unit_price_cents=1000),
                Product(product_id="P02", product_name="气泡水", product_category="饮品", unit_price_cents=500),
            ]
        )
        session.flush()
        rows = [
            (2, "O0", "2026-04-30", "S01", "P02", 1, 500),
            (3, "O1", "2026-05-01", "S01", "P01", 2, 2000),
            (4, "O1", "2026-05-01", "S01", "P02", 1, 500),
            (5, "O2", "2026-05-02", "S02", "P01", 1, 1000),
            (6, "O3", "2026-05-02", "S01", "P02", 1, 500),
        ]
        session.add_all(
            [
                Sale(
                    ingestion_run_id=run.id,
                    source_row_number=row_number,
                    order_id=order_id,
                    date=sale_date,
                    store_id=store_id,
                    product_id=product_id,
                    qty=qty,
                    amount_cents=amount,
                    amount_source="reported",
                    payment="微信",
                )
                for row_number, order_id, sale_date, store_id, product_id, qty, amount in rows
            ]
        )
        session.commit()
    yield AnalyticsService(engine)
    engine.dispose()


def test_dashboard_counts_distinct_orders_and_uses_revenue_weighted_aov(service):
    result = service.get_dashboard(
        DashboardFilters(start_date=date(2026, 5, 1), end_date=date(2026, 5, 2))
    )

    assert result.summary.revenue_cents == 4000
    assert result.summary.order_count == 3
    assert result.summary.average_order_value_cents == 1333
    assert [(point.date, point.revenue_cents, point.order_count) for point in result.daily] == [
        ("2026-05-01", 2500, 1),
        ("2026-05-02", 1500, 2),
    ]


def test_dashboard_joins_products_and_stores_for_rankings(service):
    result = service.get_dashboard(
        DashboardFilters(start_date=date(2026, 5, 1), end_date=date(2026, 5, 2))
    )

    assert [(item.product_name, item.revenue_cents) for item in result.top_products] == [
        ("牛肉poke", 3000),
        ("气泡水", 1000),
    ]
    assert [(item.store_name, item.revenue_cents) for item in result.store_comparison] == [
        ("Makai Poke", 3000),
        ("Super Souper", 1000),
    ]


def test_dashboard_applies_store_filter_and_equal_length_previous_period(service):
    result = service.get_dashboard(
        DashboardFilters(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            store_id="S01",
        )
    )

    assert result.summary.revenue_cents == 3000
    assert result.summary.order_count == 2
    assert result.summary.previous_revenue_cents == 500
    assert result.summary.revenue_change_percent == 500.0


def test_ai_queries_share_the_same_joined_analytics(service):
    revenue = service.get_revenue(
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        product_name="牛肉poke",
    )
    top_categories = service.get_top_entities(
        dimension="store_category",
        metric="revenue",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        limit=5,
    )

    assert revenue.revenue_cents == 3000
    assert revenue.order_count == 2
    assert [(item.name, item.value_cents) for item in top_categories.items] == [
        ("轻食", 3000),
        ("拉面", 1000),
    ]


def test_invalid_date_range_is_rejected_before_query(service):
    with pytest.raises(ValueError, match="start_date"):
        service.get_dashboard(
            DashboardFilters(start_date=date(2026, 5, 3), end_date=date(2026, 5, 2))
        )

