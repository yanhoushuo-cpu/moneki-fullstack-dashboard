from __future__ import annotations

from datetime import date

from app.ai.models import ChatMessage, ChatRequest


def test_beef_poke_answer_evidence_equals_database_query(analytics_and_chat):
    analytics, chat = analytics_and_chat

    response = chat.answer(ChatRequest(message="牛肉poke 六月卖了多少钱？", history=[]))
    expected = analytics.get_revenue(
        date(2026, 6, 1), date(2026, 6, 30), product_name="牛肉poke"
    )

    assert response.status == "answered"
    assert response.mode == "mock"
    assert response.evidence[0].tool == "get_revenue"
    assert response.evidence[0].parameters["product_name"] == "牛肉poke"
    assert response.evidence[0].result["revenue_cents"] == expected.revenue_cents
    assert f"¥{expected.revenue_cents / 100:,.2f}" in response.answer
    assert response.dashboard_action.start_date == "2026-06-01"
    assert response.dashboard_action.highlight_product == "牛肉poke"


def test_highest_store_category_uses_joined_database_result(analytics_and_chat):
    analytics, chat = analytics_and_chat

    response = chat.answer(ChatRequest(message="哪个品类的门店营业额最高？", history=[]))
    expected = analytics.get_top_entities(
        dimension="store_category",
        metric="revenue",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 7, 31),
        limit=1,
    )

    assert response.evidence[0].tool == "get_top_entities"
    assert response.evidence[0].result["items"][0]["name"] == expected.items[0].name
    assert response.evidence[0].result["items"][0]["value_cents"] == expected.items[0].value_cents


def test_recent_aov_direction_is_backed_by_period_comparison(analytics_and_chat):
    analytics, chat = analytics_and_chat

    response = chat.answer(ChatRequest(message="客单价最近是涨了还是跌了？", history=[]))
    expected = analytics.compare_periods(
        metric="average_order_value",
        current_start=date(2026, 7, 1),
        current_end=date(2026, 7, 31),
        previous_start=date(2026, 6, 1),
        previous_end=date(2026, 6, 30),
    )

    assert response.evidence[0].tool == "compare_periods"
    assert response.evidence[0].result["direction"] == expected.direction
    assert response.evidence[0].result["current_value"] == expected.current_value
    assert response.evidence[0].result["previous_value"] == expected.previous_value


def test_follow_up_inherits_product_but_changes_month(analytics_and_chat):
    analytics, chat = analytics_and_chat
    history = [
        ChatMessage(role="user", content="牛肉poke 六月卖了多少钱？"),
        ChatMessage(role="assistant", content="已查询六月牛肉poke营业额。"),
    ]

    response = chat.answer(ChatRequest(message="那五月呢？", history=history))
    expected = analytics.get_revenue(
        date(2026, 5, 1), date(2026, 5, 31), product_name="牛肉poke"
    )

    assert response.evidence[0].parameters["start_date"] == "2026-05-01"
    assert response.evidence[0].parameters["product_name"] == "牛肉poke"
    assert response.evidence[0].result["revenue_cents"] == expected.revenue_cents


def test_unsupported_question_returns_boundary_without_evidence(analytics_and_chat):
    _, chat = analytics_and_chat

    response = chat.answer(ChatRequest(message="明天天气怎么样？", history=[]))

    assert response.status == "unsupported"
    assert response.evidence == []
    assert response.dashboard_action is None
    assert len(response.suggestions) >= 3

