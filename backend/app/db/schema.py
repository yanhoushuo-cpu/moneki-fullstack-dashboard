from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_hash: Mapped[str] = mapped_column(String(64), unique=True)
    rule_version: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class RawSale(Base):
    __tablename__ = "raw_sales"
    __table_args__ = (UniqueConstraint("ingestion_run_id", "row_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    order_id: Mapped[str] = mapped_column(Text)
    date: Mapped[str] = mapped_column(Text)
    store_id: Mapped[str] = mapped_column(Text)
    product_id: Mapped[str] = mapped_column(Text)
    qty: Mapped[str] = mapped_column(Text)
    amount: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment: Mapped[str] = mapped_column(Text)


class Store(Base):
    __tablename__ = "stores"

    store_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    store_name: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    district: Mapped[str] = mapped_column(Text)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    product_name: Mapped[str] = mapped_column(Text)
    product_category: Mapped[str] = mapped_column(Text)
    unit_price_cents: Mapped[int] = mapped_column(Integer)


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (UniqueConstraint("ingestion_run_id", "source_row_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    source_row_number: Mapped[int] = mapped_column(Integer)
    order_id: Mapped[str] = mapped_column(Text)
    date: Mapped[str] = mapped_column(String(10))
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.store_id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"))
    qty: Mapped[int] = mapped_column(Integer)
    amount_cents: Mapped[int] = mapped_column(Integer)
    amount_source: Mapped[str] = mapped_column(String(16))
    payment: Mapped[str] = mapped_column(Text)


Index("ix_sales_date", Sale.date)
Index("ix_sales_store_id", Sale.store_id)
Index("ix_sales_product_id", Sale.product_id)


class QuarantinedSale(Base):
    __tablename__ = "quarantined_sales"
    __table_args__ = (UniqueConstraint("ingestion_run_id", "source_row_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    source_row_number: Mapped[int] = mapped_column(Integer)
    raw_json: Mapped[str] = mapped_column(Text)
    reasons_json: Mapped[str] = mapped_column(Text)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
