""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.services.cve_service import fetch_cve
from app.services.llm_service import analyze_cve

router = APIRouter()


class CVEAnalysisResponse(BaseModel):
    cve_id: str
    cve_data: dict
    analysis: str
    model_used: str


@router.get("/{cve_id}/raw", summary="Raw CVE data from NVD")
async def get_cve_raw(cve_id: str):
    data = await fetch_cve(cve_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found.")
    return data


@router.get("/{cve_id}/analyze", summary="360° CVE analysis")
async def get_cve_analysis(
    cve_id: str,
    level: str = Query("intermediate", enum=["basic", "intermediate", "advanced"]),
):
    cve_data = await fetch_cve(cve_id)
    if not cve_data:
        raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found in NVD.")

    analysis = await analyze_cve(cve_data, detail_level=level)

    return CVEAnalysisResponse(
        cve_id=cve_id,
        cve_data=cve_data,
        analysis=analysis,
        model_used=settings.ACTIVE_LLM_MODEL or "none",
    )
