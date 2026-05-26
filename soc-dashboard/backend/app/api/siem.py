""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.llm_service import analyze_siem_alert

router = APIRouter()


class SIEMAlertRequest(BaseModel):
    alert: dict
    detail_level: str = "intermediate"


@router.post("/analyze", summary="360° SIEM alert analysis")
async def analyze_alert(body: SIEMAlertRequest):
    analysis = await analyze_siem_alert(body.alert, detail_level=body.detail_level)
    return {
        "analysis": analysis,
        "model_used": settings.ACTIVE_LLM_MODEL or "none",
    }


@router.get("/mock", summary="Sample SIEM alert for testing")
async def get_mock_alert():
    return {
        "mock": True,
        "alert": {
            "@timestamp": "2026-03-09T10:23:00.000Z",
            "event.kind": "alert",
            "event.category": "intrusion_detection",
            "rule.name": "Possible CVE-2026-5167 Exploitation Attempt",
            "rule.severity": "high",
            "host.name": "workstation-042",
            "host.ip": "192.168.1.42",
            "user.name": "jdoe",
            "process.name": "OUTLOOK.EXE",
            "process.pid": 4928,
            "network.direction": "outbound",
            "destination.ip": "203.0.113.99",
            "destination.port": 445,
            "signal.reason": "Suspicious outbound SMB connection from Outlook process",
        },
    }
