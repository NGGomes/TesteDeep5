""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.cve_service import fetch_cve
from app.services.llm_service import (
    analyze_cve,
    analyze_siem_alert,
)

router = APIRouter()


class FullAnalysisRequest(BaseModel):
    cve_ids: list[str] = []
    siem_alert: Optional[dict] = None
    detail_level: str = "intermediate"
    language: str = "pt"


@router.post("/360", summary="Combined CVE + SIEM 360° analysis")
async def full_analysis(body: FullAnalysisRequest):
    results: dict = {
        "cve_analyses": {},
        "siem_analysis": None,
        "model_used": settings.ACTIVE_LLM_MODEL or "none",
    }
    for cve_id in body.cve_ids:
        cve_data = await fetch_cve(cve_id)
        if cve_data:
            results["cve_analyses"][cve_id] = await analyze_cve(
                cve_data, body.detail_level
            )
    if body.siem_alert:
        results["siem_analysis"] = await analyze_siem_alert(
            body.siem_alert, body.detail_level
        )
    return results
