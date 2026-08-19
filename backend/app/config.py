from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast


@dataclass(frozen=True)
class Settings:
    database_path: Path
    data_dir: Path
    ai_mode: Literal["mock", "provider"]
    ai_api_key: str | None
    ai_base_url: str
    ai_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        repository_root = Path(__file__).resolve().parents[2]
        ai_mode = os.getenv("AI_MODE", "mock").lower()
        if ai_mode not in {"mock", "provider"}:
            raise ValueError("AI_MODE must be either 'mock' or 'provider'")
        return cls(
            database_path=Path(
                os.getenv("DATABASE_PATH", str(repository_root / "var" / "moneki.db"))
            ),
            data_dir=Path(os.getenv("DATA_DIR", str(repository_root / "data"))),
            ai_mode=cast(Literal["mock", "provider"], ai_mode),
            ai_api_key=os.getenv("AI_API_KEY"),
            ai_base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
            ai_model=os.getenv("AI_MODEL", "gpt-5.4-mini"),
        )

