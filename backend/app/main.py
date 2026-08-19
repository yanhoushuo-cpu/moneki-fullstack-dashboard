from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_meta import router as meta_router
from app.api.routes_quality import router as quality_router


def create_app() -> FastAPI:
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
    return application


app = create_app()
