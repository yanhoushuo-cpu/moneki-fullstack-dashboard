from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_chat import router as chat_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_meta import router as meta_router
from app.api.routes_quality import router as quality_router


def create_app(static_dir: Path | None = None) -> FastAPI:
    application = FastAPI(
        title="店务罗盘 API",
        description="可审计的连锁餐饮经营分析接口",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(meta_router, prefix="/api/v1")
    application.include_router(dashboard_router, prefix="/api/v1")
    application.include_router(quality_router, prefix="/api/v1")
    application.include_router(chat_router, prefix="/api/v1")

    static_root = static_dir or Path(__file__).resolve().parents[2] / "frontend" / "dist"
    index_file = static_root / "index.html"
    assets_dir = static_root / "assets"
    if index_file.is_file():
        if assets_dir.is_dir():
            application.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @application.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")
            return FileResponse(index_file)

    return application


app = create_app()
