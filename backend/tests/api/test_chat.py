from __future__ import annotations


def test_chat_route_returns_structured_evidence(api_client):
    response = api_client.post(
        "/api/v1/chat",
        json={"message": "牛肉poke 五月卖了多少钱？", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["evidence"][0]["tool"] == "get_revenue"
    assert payload["evidence"][0]["result"]["revenue_cents"] == 4000
    assert payload["dashboard_action"]["start_date"] == "2026-05-01"


def test_chat_route_validates_input_length(api_client):
    response = api_client.post("/api/v1/chat", json={"message": "", "history": []})

    assert response.status_code == 422
