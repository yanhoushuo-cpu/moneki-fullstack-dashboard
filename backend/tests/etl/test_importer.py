from __future__ import annotations

import csv
import json

from sqlalchemy import create_engine, text

from app.etl.importer import build_database


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_importer_repairs_safe_values_and_quarantines_ambiguous_rows(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_csv(
        data_dir / "stores.csv",
        ["store_id", "store_name", "category", "district"],
        [{"store_id": "S01", "store_name": "Store One", "category": "轻食", "district": "上海·静安"}],
    )
    _write_csv(
        data_dir / "products.csv",
        ["product_id", "product_name", "product_category", "unit_price"],
        [
            {"product_id": "P01", "product_name": "牛肉poke", "product_category": "主食", "unit_price": "10.00"},
            {"product_id": "P02", "product_name": "气泡水", "product_category": "饮品", "unit_price": "5.00"},
        ],
    )
    sale_fields = ["order_id", "date", "store_id", "product_id", "qty", "amount", "payment"]
    rows = [
        {"order_id": "O1", "date": "2026-05-01", "store_id": "S01", "product_id": "P01", "qty": "2", "amount": "20.00", "payment": "微信"},
        {"order_id": "O1", "date": "2026-05-01", "store_id": "S01", "product_id": "P01", "qty": "2", "amount": "20.00", "payment": "微信"},
        {"order_id": "O2", "date": "01-05-2026", "store_id": "S01 ", "product_id": "P02", "qty": "3", "amount": "", "payment": "现金"},
        {"order_id": "O3", "date": "2026/05/02", "store_id": "S99", "product_id": "P01", "qty": "1", "amount": "10.00", "payment": "现金"},
        {"order_id": "O4", "date": "2026-05-02", "store_id": "S01", "product_id": "P99", "qty": "1", "amount": "10.00", "payment": "现金"},
        {"order_id": "O5", "date": "2026-05-02", "store_id": "S01", "product_id": "P01", "qty": "1", "amount": "-10.00", "payment": "现金"},
        {"order_id": "O6", "date": "2026-05-02", "store_id": "S01", "product_id": "P01", "qty": "-1", "amount": "10.00", "payment": "现金"},
        {"order_id": "O7", "date": "2026-05-02", "store_id": "S01", "product_id": "P01", "qty": "0", "amount": "10.00", "payment": "现金"},
        {"order_id": "O8", "date": "2026-05-02", "store_id": "s01", "product_id": "p01", "qty": "1", "amount": "10.00", "payment": "微信"},
    ]
    _write_csv(data_dir / "sales.csv", sale_fields, rows)
    database_path = tmp_path / "fixture.db"

    summary = build_database(data_dir, database_path)

    assert summary.raw_sales == 9
    assert summary.duplicate_rows_removed == 1
    assert summary.amounts_imputed == 1
    assert summary.valid_sales == 3
    assert summary.quarantined_sales == 5

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with engine.connect() as connection:
        clean_rows = connection.execute(
            text("SELECT order_id, date, store_id, amount_cents, amount_source FROM sales ORDER BY order_id")
        ).mappings().all()
        quarantine = connection.execute(
            text("SELECT reasons_json FROM quarantined_sales ORDER BY source_row_number")
        ).scalars().all()

    assert clean_rows == [
        {"order_id": "O1", "date": "2026-05-01", "store_id": "S01", "amount_cents": 2000, "amount_source": "reported"},
        {"order_id": "O2", "date": "2026-05-01", "store_id": "S01", "amount_cents": 1500, "amount_source": "imputed"},
        {"order_id": "O8", "date": "2026-05-02", "store_id": "S01", "amount_cents": 1000, "amount_source": "reported"},
    ]
    reasons = [set(json.loads(value)) for value in quarantine]
    assert {"unknown_store"} in reasons
    assert {"unknown_product"} in reasons
    assert reasons.count({"quantity_amount_sign_conflict"}) == 2
    assert {"zero_quantity_nonzero_amount"} in reasons
