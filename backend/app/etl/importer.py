from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.db.database import create_engine_for_path
from app.db.schema import (
    IngestionRun,
    Product,
    QuarantinedSale,
    RawSale,
    Sale,
    Store,
    create_schema,
)
from app.etl.models import IngestionSummary
from app.etl.normalizers import NormalizationError, normalize_date, parse_amount_to_cents


SALES_FIELDS = ("order_id", "date", "store_id", "product_id", "qty", "amount", "payment")
RULE_VERSION = "2026-08-19.1"


def _read_csv(path: Path) -> list[dict[str, str]]:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return [
        {str(key): str(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _source_hash(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in ("stores.csv", "products.csv", "sales.csv"):
        path = data_dir / name
        digest.update(name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def build_database(data_dir: Path, database_path: Path) -> IngestionSummary:
    data_dir = data_dir.resolve()
    database_path = database_path.resolve()
    for name in ("stores.csv", "products.csv", "sales.csv"):
        if not (data_dir / name).is_file():
            raise FileNotFoundError(f"required input is missing: {data_dir / name}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix="moneki-import-", suffix=".db", dir=database_path.parent, delete=False
    )
    temporary_path = Path(handle.name)
    handle.close()
    engine = create_engine_for_path(temporary_path)

    try:
        create_schema(engine)
        stores = _read_csv(data_dir / "stores.csv")
        products = _read_csv(data_dir / "products.csv")
        sales = _read_csv(data_dir / "sales.csv")
        source_hash = _source_hash(data_dir)

        with Session(engine) as session:
            ingestion = IngestionRun(
                source_hash=source_hash,
                rule_version=RULE_VERSION,
                started_at=_utc_now(),
                completed_at=None,
                summary_json=None,
            )
            session.add(ingestion)
            session.flush()

            store_ids: set[str] = set()
            for row in stores:
                store_id = row["store_id"].strip().upper()
                store_ids.add(store_id)
                session.add(
                    Store(
                        store_id=store_id,
                        store_name=row["store_name"].strip(),
                        category=row["category"].strip(),
                        district=row["district"].strip(),
                    )
                )

            product_prices: dict[str, int] = {}
            for row in products:
                product_id = row["product_id"].strip().upper()
                unit_price_cents = parse_amount_to_cents(row["unit_price"])
                product_prices[product_id] = unit_price_cents
                session.add(
                    Product(
                        product_id=product_id,
                        product_name=row["product_name"].strip(),
                        product_category=row["product_category"].strip(),
                        unit_price_cents=unit_price_cents,
                    )
                )

            # Persist dimensions before facts so SQLite can enforce foreign keys
            # even though the ORM models intentionally have no relationship graph.
            session.flush()

            seen_rows: set[tuple[str, ...]] = set()
            duplicate_rows_removed = 0
            amounts_imputed = 0
            valid_sales = 0
            quarantined_sales = 0
            issue_counts: Counter[str] = Counter()
            valid_dates: list[str] = []

            for row_number, row in enumerate(sales, start=2):
                raw = {field: row.get(field, "") for field in SALES_FIELDS}
                session.add(
                    RawSale(
                        ingestion_run_id=ingestion.id,
                        row_number=row_number,
                        **raw,
                    )
                )
                duplicate_key = tuple(raw[field] for field in SALES_FIELDS)
                if duplicate_key in seen_rows:
                    duplicate_rows_removed += 1
                    continue
                seen_rows.add(duplicate_key)

                reasons: set[str] = set()
                store_id = raw["store_id"].strip().upper()
                product_id = raw["product_id"].strip().upper()
                if store_id not in store_ids:
                    reasons.add("unknown_store")
                if product_id not in product_prices:
                    reasons.add("unknown_product")

                parsed_date = None
                try:
                    parsed_date = normalize_date(raw["date"])
                except NormalizationError:
                    reasons.add("invalid_date")

                quantity = None
                try:
                    quantity = int(raw["qty"].strip())
                except ValueError:
                    reasons.add("invalid_quantity")

                amount_cents = None
                amount_source = "reported"
                if raw["amount"].strip():
                    try:
                        amount_cents = parse_amount_to_cents(raw["amount"])
                    except NormalizationError:
                        reasons.add("invalid_amount")
                elif quantity is not None and quantity > 0 and product_id in product_prices:
                    amount_cents = quantity * product_prices[product_id]
                    amount_source = "imputed"
                    amounts_imputed += 1
                else:
                    reasons.add("missing_amount")

                if quantity is not None and amount_cents is not None:
                    if quantity == 0 and amount_cents != 0:
                        reasons.add("zero_quantity_nonzero_amount")
                    elif (quantity < 0 < amount_cents) or (amount_cents < 0 < quantity):
                        reasons.add("quantity_amount_sign_conflict")
                    elif quantity == 0 and amount_cents == 0:
                        reasons.add("zero_value_transaction")

                if (
                    not reasons
                    and quantity is not None
                    and amount_cents is not None
                    and product_id in product_prices
                    and amount_cents != quantity * product_prices[product_id]
                ):
                    reasons.add("amount_unit_price_mismatch")

                if reasons:
                    ordered_reasons = sorted(reasons)
                    issue_counts.update(ordered_reasons)
                    quarantined_sales += 1
                    session.add(
                        QuarantinedSale(
                            ingestion_run_id=ingestion.id,
                            source_row_number=row_number,
                            raw_json=json.dumps(raw, ensure_ascii=False, sort_keys=True),
                            reasons_json=json.dumps(ordered_reasons, ensure_ascii=False),
                        )
                    )
                    continue

                assert parsed_date is not None
                assert quantity is not None
                assert amount_cents is not None
                normalized_date = parsed_date.isoformat()
                valid_dates.append(normalized_date)
                valid_sales += 1
                session.add(
                    Sale(
                        ingestion_run_id=ingestion.id,
                        source_row_number=row_number,
                        order_id=raw["order_id"].strip(),
                        date=normalized_date,
                        store_id=store_id,
                        product_id=product_id,
                        qty=quantity,
                        amount_cents=amount_cents,
                        amount_source=amount_source,
                        payment=raw["payment"].strip(),
                    )
                )

            summary = IngestionSummary(
                source_hash=source_hash,
                raw_sales=len(sales),
                duplicate_rows_removed=duplicate_rows_removed,
                amounts_imputed=amounts_imputed,
                valid_sales=valid_sales,
                quarantined_sales=quarantined_sales,
                date_min=min(valid_dates) if valid_dates else None,
                date_max=max(valid_dates) if valid_dates else None,
                issue_counts=dict(sorted(issue_counts.items())),
            )
            ingestion.completed_at = _utc_now()
            ingestion.summary_json = summary.to_json()
            session.commit()

        engine.dispose()
        os.replace(temporary_path, database_path)
        return summary
    except Exception:
        engine.dispose()
        temporary_path.unlink(missing_ok=True)
        raise
