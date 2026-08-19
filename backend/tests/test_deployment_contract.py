from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_container_and_render_blueprint_share_runtime_contract():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "${PORT:-8000}" in dockerfile
    assert "os.environ.get('PORT', '8000')" in dockerfile
    assert "runtime: docker" in blueprint
    assert "plan: free" in blueprint
    assert "healthCheckPath: /api/v1/health" in blueprint
    assert "value: mock" in blueprint
