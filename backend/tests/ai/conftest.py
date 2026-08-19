from __future__ import annotations

from pathlib import Path

import pytest

from app.ai.mock_planner import MockPlanner
from app.ai.service import ChatService
from app.analytics.service import AnalyticsService
from app.db.database import create_engine_for_path
from app.etl.importer import build_database


@pytest.fixture(scope="module")
def analytics_and_chat(tmp_path_factory):
    repository_root = Path(__file__).resolve().parents[3]
    database_path = tmp_path_factory.mktemp("ai") / "real.db"
    build_database(repository_root / "data", database_path)
    engine = create_engine_for_path(database_path)
    analytics = AnalyticsService(engine)
    chat = ChatService(analytics=analytics, planner=MockPlanner(analytics.get_meta()))
    yield analytics, chat
    engine.dispose()

