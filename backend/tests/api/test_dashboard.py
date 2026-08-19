from __future__ import annotations


def test_dashboard_contract_contains_backend_formatted_metrics(api_client):
    response = api_client.get(
        "/api/v1/dashboard?start_date=2026-05-01&end_date=2026-05-02"
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "filters",
        "summary",
        "daily",
        "top_products",
        "store_comparison",
        "coverage",
    }
    assert payload["summary"]["revenue"] == {"cents": 4000, "formatted": "¥40.00"}
    assert payload["summary"]["order_count"] == 2
    assert payload["summary"]["average_order_value"] == {"cents": 2000, "formatted": "¥20.00"}
    assert payload["daily"][0]["order_count"] == 1
    assert payload["top_products"][0]["product_name"] == "牛肉poke"


def test_meta_health_and_quality_expose_current_ingestion(api_client):
    health = api_client.get("/api/v1/health")
    meta = api_client.get("/api/v1/meta")
    quality = api_client.get("/api/v1/data-quality")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["ingestion_run_id"] == 1
    assert meta.json()["date_range"] == {"min": "2026-05-01", "max": "2026-05-02"}
    assert meta.json()["stores"][0]["store_name"] == "Makai Poke"
    assert quality.json()["summary"]["valid_sales"] == 3
    assert quality.json()["rules"][0]["code"] == "duplicate_row"

