from __future__ import annotations


def test_dashboard_rejects_reversed_date_range(api_client):
    response = api_client.get(
        "/api/v1/dashboard?start_date=2026-05-03&end_date=2026-05-02"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "start_date must not be after end_date"


def test_dashboard_rejects_unknown_store(api_client):
    response = api_client.get(
        "/api/v1/dashboard?start_date=2026-05-01&end_date=2026-05-02&store_id=S99"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown store_id: S99"
