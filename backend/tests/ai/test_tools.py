from __future__ import annotations

import pytest

from app.ai.models import ToolCall
from app.ai.tools import ToolExecutor


def test_executor_rejects_tools_outside_allowlist(analytics_and_chat):
    analytics, _ = analytics_and_chat
    executor = ToolExecutor(analytics)

    with pytest.raises(ValueError, match="unsupported tool"):
        executor.execute(ToolCall(name="run_sql", arguments={"sql": "DROP TABLE sales"}))
