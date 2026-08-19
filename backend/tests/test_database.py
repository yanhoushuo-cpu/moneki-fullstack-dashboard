from __future__ import annotations

from sqlalchemy import inspect

from app.db.database import create_engine_for_path
from app.db.schema import create_schema


def test_create_schema_builds_auditable_sales_tables(tmp_path):
    engine = create_engine_for_path(tmp_path / "test.db")

    create_schema(engine)

    assert set(inspect(engine).get_table_names()) == {
        "ingestion_runs",
        "products",
        "quarantined_sales",
        "raw_sales",
        "sales",
        "stores",
    }


def test_sales_table_has_query_indexes(tmp_path):
    engine = create_engine_for_path(tmp_path / "test.db")
    create_schema(engine)

    index_names = {item["name"] for item in inspect(engine).get_indexes("sales")}

    assert {"ix_sales_date", "ix_sales_product_id", "ix_sales_store_id"} <= index_names
