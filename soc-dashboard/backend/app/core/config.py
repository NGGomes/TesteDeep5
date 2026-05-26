from __future__ import annotations

from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """Find the project root by looking for .env or pyproject.toml."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / ".env").exists() or (ancestor / "pyproject.toml").exists():
            return ancestor
    try:
        return here.parents[4]
    except IndexError:
        return here.parent


_ROOT     = _find_project_root()
_ENV_FILE = str(_ROOT / ".env") if (_ROOT / ".env").exists() else ".env"


class Settings(BaseSettings):

    LLM_TIMEOUT_SECONDS:    int = 120
    API_TIMEOUT_SECONDS:    int = 120
    OLLAMA_REQUEST_TIMEOUT: int = 180

    # Agent 1 is rule-based — no LLM.
    # FastAPI extension uses LLM_PROVIDER2 (same model as Agent 2).
    LLM_PROVIDER:  str = "none"    # not used for analysis — kept for compat
    LLM_PROVIDER2: str = "ollama"  # Agent 2 / extension analysis model

    OLLAMA_MODEL:    str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL:   str = "claude-haiku-4-5-20251001"

    OPENAI_API_KEY: str = ""
    LITELLM_MODEL:  str = "gpt-4o-mini"
    LITELLM_MODEL2: str = "gpt-4o-mini"

    ACTIVE_LLM_MODEL: str = ""

    NVD_API_KEY:   str = ""
    CVE_CACHE_TTL: int = 86400

    ELASTIC_URL:        str  = "https://localhost:9200"
    ELASTIC_USERNAME:   str  = "elastic"
    ELASTIC_PASSWORD:   str  = "changeme"
    ELASTIC_VERIFY_SSL: bool = False

    APP_ENV:    str = "development"
    APP_PORT:   int = 8000
    SECRET_KEY: str = "dev-secret-key"
    LOG_LEVEL:  str = "DEBUG"

    MAX_TOKENS_PER_REQUEST: int = 2000

    model_config = SettingsConfigDict(
        env_file          = _ENV_FILE,
        env_file_encoding = "utf-8",
        case_sensitive    = False,
        extra             = "ignore",
    )

    @model_validator(mode="after")
    def _resolve_active_model(self) -> "Settings":
        """Use LLM_PROVIDER2 (Agent 2 model) for all LLM analysis.
        Agent 1 is rule-based — no LLM needed.
        """
        provider = self.LLM_PROVIDER2.lower().strip()

        if provider == "ollama":
            self.ACTIVE_LLM_MODEL = f"ollama/{self.OLLAMA_MODEL}"
        elif provider == "anthropic":
            self.ACTIVE_LLM_MODEL = f"anthropic/{self.ANTHROPIC_MODEL}"
        elif provider == "openai":
            self.ACTIVE_LLM_MODEL = self.LITELLM_MODEL2
        elif provider in ("none", ""):
            self.ACTIVE_LLM_MODEL = ""
        else:
            self.ACTIVE_LLM_MODEL = provider

        # Keep LLM_PROVIDER in sync for any legacy code that reads it
        self.LLM_PROVIDER = provider

        return self


settings = Settings()