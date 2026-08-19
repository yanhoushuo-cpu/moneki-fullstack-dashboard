from __future__ import annotations

from functools import lru_cache

from app.ai.mock_planner import MockPlanner
from app.ai.provider import ProviderPlanner
from app.ai.service import ChatService
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


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    settings = get_settings()
    analytics = get_analytics_service()
    if settings.ai_mode == "provider" and settings.ai_api_key:
        planner = ProviderPlanner(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
        )
    else:
        planner = MockPlanner(analytics.get_meta())
    return ChatService(analytics=analytics, planner=planner)
