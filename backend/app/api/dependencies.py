from __future__ import annotations

from functools import lru_cache

from app.analytics.service import AnalyticsService
from app.config import Settings
from app.db.database import create_engine_for_path
from app.etl.importer import build_database


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache(maxsize=1)
def get_analytics_service() -> AnalyticsService:
    settings = get_settings()
    if not settings.database_path.exists():
        build_database(settings.data_dir, settings.database_path)
    return AnalyticsService(create_engine_for_path(settings.database_path))

