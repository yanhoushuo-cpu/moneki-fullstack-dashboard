from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class IngestionSummary:
    source_hash: str
    raw_sales: int
    duplicate_rows_removed: int
    amounts_imputed: int
    valid_sales: int
    quarantined_sales: int
    date_min: str | None
    date_max: str | None
    issue_counts: dict[str, int] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

