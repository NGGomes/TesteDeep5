from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import (
    BACKEND_PORT,
    BACKEND_HOST,
    AGENT2_REPORTS_DIR,
    AGENT1_REPORTS_DIR,
    get_dashboard_config,
    LLM_PROVIDER2,
    ANTHROPIC_MODEL,
    OLLAMA_MODEL,
    LITELLM_MODEL2,
    AGENT2_TIMEOUT_SECONDS,
)

app = FastAPI(title="SOC Dashboard API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _active_model() -> str:
    if LLM_PROVIDER2 == "anthropic":
        return ANTHROPIC_MODEL
    if LLM_PROVIDER2 == "ollama":
        return OLLAMA_MODEL
    return LITELLM_MODEL2


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "env": "production",
        "model": _active_model(),
        "provider": LLM_PROVIDER2,
    }


@app.get("/api/config")
async def get_config():
    cfg = get_dashboard_config()
    cfg.update(
        {
            "model": _active_model(),
            "active_model": _active_model(),
            "llm_provider": LLM_PROVIDER2,
            "llm_timeout_seconds": AGENT2_TIMEOUT_SECONDS,
            "api_timeout_seconds": 30,
        }
    )
    return cfg


@app.get("/api/agent2/reports")
async def get_agent2_reports():
    """"""
    import json

    reports = []
    if AGENT2_REPORTS_DIR.exists():
        for f in sorted(
            AGENT2_REPORTS_DIR.glob("*.json"), reverse=True
        )[:20]:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    reports.append(json.load(fp))
            except Exception:
                pass
    return reports


@app.get("/api/agent1/reports")
async def get_agent1_reports():
    """"""
    import json

    reports = []
    if AGENT1_REPORTS_DIR.exists():
        for f in sorted(AGENT1_REPORTS_DIR.glob("ag1_*.json"), reverse=True)[:20]:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    reports.append(json.load(fp))
            except Exception:
                pass
    return reports


@app.get("/api/graph/state")
async def get_graph_state():
    """"""
    import json

    graph_file = AGENT1_REPORTS_DIR / "hypothesis_graph.json"
    if graph_file.exists():
        try:
            with open(graph_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "nodes": [],
        "edges": [],
        "confirmed_hypotheses": [],
        "kill_chain_progress": {},
        "total_evidence_windows": 0,
    }


# ── Register API routers ────────────────────────────────────────────────────
try:
    from app.api import cve as _cve_mod
    from app.api import siem as _siem_mod
    from app.api import analysis as _analysis_mod
    from app.api import health as _health_mod

    app.include_router(_cve_mod.router, prefix="/api/v1/cve", tags=["CVE"])
    app.include_router(_siem_mod.router, prefix="/api/v1/siem", tags=["SIEM"])
    app.include_router(
        _analysis_mod.router, prefix="/api/v1/analysis", tags=["Analysis"]
    )
    app.include_router(_health_mod.router, prefix="/api/v1", tags=["Health"])
except ImportError as _e:
    import logging

    logging.getLogger(__name__).warning(f"Could not load API routers: {_e}")

# ── Extension-compatible wrapper routes ─────────────────────────────────────
# The Chrome extension calls these specific endpoints


@app.post("/api/v1/analysis/cve")
async def ext_cve_analysis(body: dict):
    """Extension compat: POST {cve_id, level} → CVE analysis"""
    from app.services.cve_service import fetch_cve
    from app.services.llm_service import analyze_cve
    from app.core.config import settings

    cve_id = (body.get("cve_id") or "").strip().upper()
    level = body.get("level", "intermediate")
    if not cve_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Missing cve_id")
    cve_data = await fetch_cve(cve_id)
    if not cve_data:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"{cve_id} not found in NVD")
    analysis = await analyze_cve(cve_data, detail_level=level)
    return {
        "cve_id": cve_id,
        "cve_data": cve_data,
        "analysis": analysis,
        "model_used": settings.ACTIVE_LLM_MODEL or "none",
    }


@app.post("/api/v1/analysis/siem")
async def ext_siem_analysis(body: dict):
    """Extension compat: POST {alert} → SIEM analysis"""
    from app.services.llm_service import analyze_siem_alert
    from app.core.config import settings

    alert = body.get("alert", body)
    analysis = await analyze_siem_alert(
        alert, detail_level=body.get("detail_level", "intermediate")
    )
    return {
        "analysis": analysis,
        "model_used": settings.ACTIVE_LLM_MODEL or "none",
    }


@app.post("/api/v1/analysis/chat")
async def ext_chat(body: dict):
    """Extension compat: POST {messages} → chat reply"""
    from app.services.llm_service import _call_llm
    from app.core.config import settings

    messages = body.get("messages", [])
    if not messages:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Missing messages")
    # Build prompt from conversation history
    history = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in messages
        if m.get("role") in ("user", "assistant", "system")
    )
    reply, model = await _call_llm(history)
    return {
        "reply": reply,
        "model_used": model or settings.ACTIVE_LLM_MODEL or "none",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
