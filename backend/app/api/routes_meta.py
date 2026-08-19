from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.service import AnalyticsService
from app.api.dependencies import get_analytics_service
from app.models.api import (
    DateRangeResponse,
    HealthResponse,
    MetaResponse,
    StoreOptionResponse,
)


router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health(service: AnalyticsService = Depends(get_analytics_service)) -> HealthResponse:
    meta = service.get_meta()
    return HealthResponse(status="ok", database="ready", ingestion_run_id=meta.ingestion_run_id)


@router.get("/meta", response_model=MetaResponse)
def meta(service: AnalyticsService = Depends(get_analytics_service)) -> MetaResponse:
    result = service.get_meta()
    presets: list[dict[str, str]] = []
    if result.date_min and result.date_max:
        presets.append({"label": "全部数据", "start_date": result.date_min, "end_date": result.date_max})
        for month, label in (("05", "五月"), ("06", "六月"), ("07", "七月")):
            presets.append(
                {
                    "label": label,
                    "start_date": f"2026-{month}-01",
                    "end_date": {"05": "2026-05-31", "06": "2026-06-30", "07": "2026-07-31"}[month],
                }
            )
    return MetaResponse(
        date_range=DateRangeResponse(min=result.date_min, max=result.date_max),
        stores=[StoreOptionResponse(**store.__dict__) for store in result.stores],
        ingestion_run_id=result.ingestion_run_id,
        presets=presets,
    )

