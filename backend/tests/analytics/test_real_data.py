from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.analytics.service import AnalyticsService
from app.db.database import create_engine_for_path
from app.etl.importer import build_database


def test_required_questions_match_independent_real_database_queries(tmp_path):
    repository_root = Path(__file__).resolve().parents[3]
    database_path = tmp_path / "real.db"
    build_database(repository_root / "data", database_path)
    engine = create_engine_for_path(database_path)
    service = AnalyticsService(engine)

    beef_poke = service.get_revenue(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        product_name="牛肉poke",
    )
    top_category = service.get_top_entities(
        dimension="store_category",
        metric="revenue",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 7, 31),
        limit=1,
    )

    with engine.connect() as connection:
        expected_beef = connection.execute(
            text(
                """
                SELECT SUM(s.amount_cents)
                FROM sales s JOIN products p ON p.product_id = s.product_id
                WHERE s.date BETWEEN '2026-06-01' AND '2026-06-30'
                  AND p.product_name = '牛肉poke'
                """
            )
        ).scalar_one()
        expected_category = connection.execute(
            text(
                """
                SELECT st.category, SUM(s.amount_cents) AS revenue
                FROM sales s JOIN stores st ON st.store_id = s.store_id
                WHERE s.date BETWEEN '2026-05-01' AND '2026-07-31'
                GROUP BY st.category
                ORDER BY revenue DESC, st.category ASC
                LIMIT 1
                """
            )
        ).one()

    assert beef_poke.revenue_cents == expected_beef
    assert (top_category.items[0].name, top_category.items[0].value_cents) == tuple(expected_category)
    engine.dispose()
