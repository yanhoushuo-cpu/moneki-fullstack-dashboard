from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.models import DashboardFilters
from app.analytics.service import AnalyticsService
from app.api.dependencies import get_analytics_service
from app.models.api import (
    CoverageResponse,
    DailyResponse,
    DashboardResponse,
    FiltersResponse,
    StoreComparisonResponse,
    SummaryResponse,
    TopProductResponse,
    money,
)


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    start_date: date = Query(),
    end_date: date = Query(),
    store_id: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> DashboardResponse:
    normalized_store = store_id.strip().upper() if store_id else None
    available_stores = {store.store_id for store in service.get_meta().stores}
    if normalized_store and normalized_store not in available_stores:
        raise HTTPException(status_code=400, detail=f"unknown store_id: {normalized_store}")
    filters = DashboardFilters(
        start_date=start_date,
        end_date=end_date,
        store_id=normalized_store,
    )
    try:
        result = service.get_dashboard(filters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DashboardResponse(
        filters=FiltersResponse(
            start_date=result.filters.start_date.isoformat(),
            end_date=result.filters.end_date.isoformat(),
            store_id=result.filters.store_id,
        ),
        summary=SummaryResponse(
            revenue=money(result.summary.revenue_cents),
            order_count=result.summary.order_count,
            average_order_value=money(result.summary.average_order_value_cents),
            previous_revenue=money(result.summary.previous_revenue_cents),
            previous_order_count=result.summary.previous_order_count,
            previous_average_order_value=money(
                result.summary.previous_average_order_value_cents
            ),
            revenue_change_percent=result.summary.revenue_change_percent,
            order_change_percent=result.summary.order_change_percent,
            average_order_value_change_percent=result.summary.average_order_value_change_percent,
        ),
        daily=[
            DailyResponse(
                date=point.date,
                revenue=money(point.revenue_cents),
                order_count=point.order_count,
                average_order_value=money(point.average_order_value_cents),
            )
            for point in result.daily
        ],
        top_products=[
            TopProductResponse(
                product_id=item.product_id,
                product_name=item.product_name,
                product_category=item.product_category,
                quantity=item.quantity,
                revenue=money(item.revenue_cents),
                order_count=item.order_count,
            )
            for item in result.top_products
        ],
        store_comparison=[
            StoreComparisonResponse(
                store_id=item.store_id,
                store_name=item.store_name,
                category=item.category,
                district=item.district,
                revenue=money(item.revenue_cents),
                order_count=item.order_count,
                share_percent=item.share_percent,
            )
            for item in result.store_comparison
        ],
        coverage=CoverageResponse(**result.coverage.__dict__),
    )

