from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_production_app_serves_assets_and_spa_fallback(tmp_path: Path):
    static_dir = tmp_path / "dist"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<main>店务罗盘</main>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('ready')", encoding="utf-8")

    client = TestClient(create_app(static_dir=static_dir))

    assert client.get("/").text == "<main>店务罗盘</main>"
    assert client.get("/reports/june").text == "<main>店务罗盘</main>"
    assert client.get("/assets/app.js").text == "console.log('ready')"
    assert client.get("/api/v1/not-found").status_code == 404
