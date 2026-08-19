from __future__ import annotations

from datetime import date

import pytest

from app.etl.normalizers import NormalizationError, normalize_date, parse_amount_to_cents


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-05-01", date(2026, 5, 1)),
        ("01-05-2026", date(2026, 5, 1)),
        ("2026/05/01", date(2026, 5, 1)),
    ],
)
def test_normalize_date_accepts_only_declared_formats(raw, expected):
    assert normalize_date(raw) == expected


def test_normalize_date_rejects_ambiguous_slash_format():
    with pytest.raises(NormalizationError):
        normalize_date("05/01/2026")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("66.00", 6600), ("¥66.00", 6600), ("12.345", 1235)],
)
def test_parse_amount_uses_integer_cents_and_half_up_rounding(raw, expected):
    assert parse_amount_to_cents(raw) == expected

