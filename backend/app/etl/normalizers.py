from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class NormalizationError(ValueError):
    """Raised when an input cannot be normalized without guessing."""


DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d")


def normalize_date(value: str) -> date:
    cleaned = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    raise NormalizationError(f"unsupported date format: {value!r}")


def parse_amount_to_cents(value: str) -> int:
    cleaned = value.strip().removeprefix("¥").strip()
    if not cleaned:
        raise NormalizationError("amount is empty")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise NormalizationError(f"invalid amount: {value!r}") from exc
    cents = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)

