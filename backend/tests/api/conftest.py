from __future__ import annotations

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.mock_planner import MockPlanner
from app.ai.service import ChatService
from app.analytics.service import AnalyticsService
from app.api.dependencies import get_analytics_service, get_chat_service
from app.db.database import create_engine_for_path
from app.db.schema import IngestionRun, Product, Sale, Store, create_schema
from app.main import app


@pytest.fixture()
def api_client(tmp_path):
    engine = create_engine_for_path(tmp_path / "api.db")
    create_schema(engine)
    with Session(engine) as session:
        run = IngestionRun(
            source_hash="b" * 64,
            rule_version="test",
            started_at=datetime(2026, 8, 19, 10, 0),
            completed_at=datetime(2026, 8, 19, 10, 1),
            summary_json=json.dumps(
                {
                    "raw_sales": 4,
                    "duplicate_rows_removed": 1,
                    "amounts_imputed": 1,
                    "valid_sales": 3,
                    "quarantined_sales": 0,
                    "issue_counts": {},
                }
            ),
        )
        session.add(run)
        session.flush()
        session.add_all(
            [
                Store(store_id="S01", store_name="Makai Poke", category="轻食", district="上海·静安"),
                Product(product_id="P01", product_name="牛肉poke", product_category="主食", unit_price_cents=1000),
            ]
        )
        session.flush()
        session.add_all(
            [
                Sale(ingestion_run_id=run.id, source_row_number=2, order_id="O1", date="2026-05-01", store_id="S01", product_id="P01", qty=2, amount_cents=2000, amount_source="reported", payment="微信"),
                Sale(ingestion_run_id=run.id, source_row_number=3, order_id="O1", date="2026-05-01", store_id="S01", product_id="P01", qty=1, amount_cents=1000, amount_source="reported", payment="微信"),
                Sale(ingestion_run_id=run.id, source_row_number=4, order_id="O2", date="2026-05-02", store_id="S01", product_id="P01", qty=1, amount_cents=1000, amount_source="imputed", payment="现金"),
            ]
        )
        session.commit()

    analytics = AnalyticsService(engine)
    chat = ChatService(analytics=analytics, planner=MockPlanner(analytics.get_meta()))
    app.dependency_overrides[get_analytics_service] = lambda: analytics
    app.dependency_overrides[get_chat_service] = lambda: chat
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()
