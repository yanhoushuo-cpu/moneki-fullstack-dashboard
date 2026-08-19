from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.service import AnalyticsService
from app.api.dependencies import get_analytics_service
from app.models.api import DataQualityResponse, QualityRuleResponse


router = APIRouter(tags=["data quality"])


RULES = [
    QualityRuleResponse(code="duplicate_row", label="完全重复记录", action="保留首次出现的记录"),
    QualityRuleResponse(code="normalized_identifier", label="ID 空格与大小写", action="去空格并统一大写"),
    QualityRuleResponse(code="normalized_date", label="三种日期格式", action="统一为 YYYY-MM-DD"),
    QualityRuleResponse(code="normalized_currency", label="金额货币符号", action="移除 ¥ 并保存为整数分"),
    QualityRuleResponse(code="imputed_amount", label="安全补全金额", action="以有效数量乘商品单价补全"),
    QualityRuleResponse(code="quarantined_row", label="歧义或脏外键", action="隔离并记录全部原因"),
]


@router.get("/data-quality", response_model=DataQualityResponse)
def data_quality(
    service: AnalyticsService = Depends(get_analytics_service),
) -> DataQualityResponse:
    result = service.get_data_quality()
    return DataQualityResponse(
        ingestion_run_id=result.ingestion_run_id,
        source_hash=result.source_hash,
        rule_version=result.rule_version,
        updated_at=result.updated_at,
        summary=result.summary,
        rules=RULES,
    )

