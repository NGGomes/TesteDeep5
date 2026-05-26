""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="Server health and active model")
async def health():
    """"""
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "model": settings.ACTIVE_LLM_MODEL or "none (LLM disabled)",
        "provider": settings.LLM_PROVIDER,
    }
