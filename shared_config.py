"""
Configuração partilhada entre todos os módulos.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

_config_logger = logging.getLogger("config")

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Load .env / env file ──────────────────────────────────────────────────────
# Priority: .env > env > already-set environment variables.
# Uses python-dotenv if available, otherwise parses manually.
def _load_env_file() -> None:
    """Load environment variables from .env or env file in the project root."""
    candidates = [_PROJECT_ROOT / ".env", _PROJECT_ROOT / "env"]
    env_file = next((f for f in candidates if f.exists()), None)
    if env_file is None:
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)  # .env always wins over system env
        _config_logger.debug(
            f"[config] Loaded env from {env_file.name} (python-dotenv)"
        )
        return
    except ImportError:
        pass  # fall through to manual parser

    # Manual parser — handles KEY=VALUE, inline comments, quoted values
    try:
        with open(env_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, raw = line.partition("=")
                key = key.strip()
                # Strip inline comment (# not inside quotes)
                raw = raw.split("#")[0].strip()
                # Strip surrounding quotes
                if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
                    raw = raw[1:-1]
                if key:
                    os.environ[key] = raw  # .env always wins
        _config_logger.debug(
            f"[config] Loaded env from {env_file.name} (manual parser)"
        )
    except Exception as exc:
        _config_logger.warning(f"[config] Failed to load {env_file.name}: {exc}")


_load_env_file()
# ─────────────────────────────────────────────────────────────────────────────


def _env_int(name: str, default: int, min_val: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default

    if value < min_val:
        return min_val
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "1" if default else "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_float(
    name: str, default: float, min_val: float = 0.0, max_val: float = 1.0
) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default

    if value < min_val or value > max_val:
        return default
    return value


PORT: int = _env_int("PORT", 5001)
DASHBOARD_PORT: int = PORT
DASHBOARD_HOST: str = _env_str("DASHBOARD_HOST", "localhost")
DASHBOARD_THEME: str = _env_str("DASHBOARD_THEME", "dark")
DASHBOARD_WINDOW_DAYS: int = _env_int("DASHBOARD_WINDOW_DAYS", 1)
DEFAULT_WINDOW_DAYS: int = DASHBOARD_WINDOW_DAYS
DEFAULT_WINDOW_HOURS: int = DEFAULT_WINDOW_DAYS * 24
DEFAULT_WINDOW_SECONDS: int = DEFAULT_WINDOW_DAYS * 24 * 60 * 60
DEFAULT_WINDOW_MS: int = DEFAULT_WINDOW_SECONDS * 1000
DEFAULT_WINDOW_MINUTES: int = DEFAULT_WINDOW_DAYS * 24 * 60
WINDOW_HOURS: int = _env_int("WINDOW_HOURS", DEFAULT_WINDOW_HOURS)
STEP_HOURS: int = _env_int("STEP_HOURS", 1)
STEP_SECONDS: int = STEP_HOURS * 3600
MIN_ALERTS_WINDOW: int = _env_int("MIN_ALERTS_WINDOW", 3)
DEFAULT_ACTIVE_WINDOW_MINUTES: int = _env_int("DEFAULT_ACTIVE_WINDOW_MINUTES", 15)
DASHBOARD_UPDATE_INTERVAL_MS: int = _env_int("DASHBOARD_UPDATE_INTERVAL_MS", 5000)
DASHBOARD_HISTORY_LIMIT: int = _env_int("DASHBOARD_HISTORY_LIMIT", 200)
DASHBOARD_AGENT2_REPORTS_LIMIT: int = _env_int("DASHBOARD_AGENT2_REPORTS_LIMIT", 20)

BACKEND_PORT: int = _env_int("BACKEND_PORT", 8000)
BACKEND_HOST: str = _env_str("BACKEND_HOST", "127.0.0.1")
BACKEND_WORKERS: int = _env_int("BACKEND_WORKERS", 1)
BACKEND_LOG_LEVEL: str = _env_str("BACKEND_LOG_LEVEL", "warning")

AGENT2_POLL_SECONDS: int = _env_int("AGENT2_POLL_SECONDS", 5)
AGENT2_RUN_ONCE: bool = _env_bool("AGENT2_RUN_ONCE", False)
AGENT2_TIMEOUT_SECONDS: int = _env_int(
    "AGENT2_TIMEOUT_SECONDS", 120
)  # 2min default — override in .env
AGENT2_CVE_CODES: str = _env_str(
    "AGENT2_CVE_CODES", ""
)  # comma-separated additional CVEs

LLM_PROVIDER: str = _env_str(
    "LLM_PROVIDER", "none"
).lower()  # Agent 1 — no LLM (rule-based)
LLM_PROVIDER2: str = _env_str(
    "LLM_PROVIDER2", "none"
).lower()  # Agent 2 + FastAPI extension
AGENT1_LLM_PROVIDER: str = "none"  # Agent 1 is always rule-based — never uses LLM
AGENT2_LLM_PROVIDER: str = LLM_PROVIDER2

OLLAMA_BASE_URL: str = _env_str("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = _env_str("OLLAMA_MODEL", "llama3.2")
OLLAMA_HOST: str = OLLAMA_BASE_URL
OLLAMA_AUTO_PULL: bool = _env_bool("OLLAMA_AUTO_PULL", True)
OLLAMA_START_WAIT: int = _env_int("OLLAMA_START_WAIT_S", 15)

ANTHROPIC_API_KEY: str = _env_str("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = _env_str("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

OPENAI_API_KEY: str = _env_str("OPENAI_API_KEY", "")
LITELLM_MODEL: str = _env_str("LITELLM_MODEL", "gpt-4o-mini")
LITELLM_MODEL2: str = _env_str("LITELLM_MODEL2", "gpt-4o-mini")

CISO_WINDOW_MINUTES: int = _env_int("CISO_WINDOW_MINUTES", 15)
CISO_WINDOW_LOOKBACK: bool = _env_bool("CISO_WINDOW_LOOKBACK", True)
CISO_WINDOW_FORWARD: bool = _env_bool("CISO_WINDOW_FORWARD", False)
CISO_MIN_ALERTS_PER_WINDOW: int = _env_int("CISO_MIN_ALERTS_PER_WINDOW", 1)
TRIGGER_ON_WINDOW_EXPIRY: bool = _env_bool("TRIGGER_ON_WINDOW_EXPIRY", True)
TRIGGER_EXPIRY_BUFFER_SECONDS: int = _env_int("TRIGGER_EXPIRY_BUFFER_SECONDS", 5)
WINDOW_OVERLAP_RATIO: float = _env_float("WINDOW_OVERLAP_RATIO", 0.5, 0.0, 1.0)
CISO_DECISION_TIMEOUT_SECONDS: int = _env_int("CISO_DECISION_TIMEOUT_SECONDS", 120)
CISO_DECISION_ENABLED: bool = _env_bool("CISO_DECISION_ENABLED", True)

STREAM_SPEED_FACTOR: float = _env_float("STREAM_SPEED_FACTOR", 0.05, 0.001, 1.0)
STREAM_TIMEOUT_MINUTES: int = _env_int("STREAM_TIMEOUT_MINUTES", 15)
STREAM_STEP_MINUTES: int = _env_int("STREAM_STEP_MINUTES", 15)
TIMEOUT_UNIT_MINUTES: int = _env_int("DASHBOARD_TIMEOUT_UNIT_MINUTES", 15)

PROBABILISTIC_VARIANCE: float = _env_float("PROBABILISTIC_VARIANCE", 0.10)
PROBABILISTIC_MAX_HYPOTHESES: int = _env_int("PROBABILISTIC_MAX_HYPOTHESES", 3)
PROBABILISTIC_TIMEOUT_AUTO: bool = _env_bool("PROBABILISTIC_TIMEOUT_AUTO", True)

CONFIRMATION_THRESHOLD: float = _env_float("CONFIRMATION_THRESHOLD", 0.85, 0.5, 0.99)
MAX_HYPOTHESES_PER_NODE: int = PROBABILISTIC_MAX_HYPOTHESES
HYPOTHESIS_DECAY_HOURS: float = _env_float("HYPOTHESIS_DECAY_HOURS", 24.0, 0.0, 168.0)
MAX_PARALLEL_WINDOWS: int = _env_int("MAX_PARALLEL_WINDOWS", 10, 1)
CONVERGENCE_STD_THRESHOLD: float = _env_float(
    "CONVERGENCE_STD_THRESHOLD", 0.05, 0.01, 0.2
)
INCOHERENCE_THRESHOLD: float = _env_float("INCOHERENCE_THRESHOLD", 0.3, 0.1, 0.5)

PROJECT_ROOT: Path = _PROJECT_ROOT
REPORTS_DIR: Path = _PROJECT_ROOT / "reports"
AGENT1_REPORTS_DIR: Path = REPORTS_DIR / "agent1"
AGENT2_REPORTS_DIR: Path = REPORTS_DIR / "agent2"
LOG_DIR: Path = _PROJECT_ROOT / "logs"
CONTROL_FILE: Path = _PROJECT_ROOT / "reports" / "control" / "window_request.json"
INPUT_DATA_FILE: Path = PROJECT_ROOT / "projD.txt"
CACHE_FILE: Path = PROJECT_ROOT / "reports" / "agent1" / "ciso_score_cache.json"
CLASS_LOG_FILE: Path = PROJECT_ROOT / "soc_classification_log.json"
DATASET_BOUNDS_FILE: Path = AGENT1_REPORTS_DIR / "dataset_bounds.json"
FRONTEND_DIST_DIR = PROJECT_ROOT / "soc-dashboard" / "frontend" / "dist"

WINDOW_MODE: str = _env_str("WINDOW_MODE", "fixed").lower()

# ── Texer (LaTeX → PDF rendering server) ─────────────────────────────────────
TEXER_PORT: int = _env_int("TEXER_PORT", 5002)
TEXER_HOST: str = _env_str("TEXER_HOST", "localhost")
TEXER_COMPILE_TIMEOUT: int = _env_int(
    "TEXER_COMPILE_TIMEOUT", 60
)  # pdflatex timeout (s)
TEXER_COMPILE_RUNS: int = _env_int("TEXER_COMPILE_RUNS", 2)  # pdflatex passes

# ── LLM tuning (Agent 2) ──────────────────────────────────────────────────────
AGENT2_MAX_TOKENS: int = _env_int(
    "AGENT2_MAX_TOKENS", 1200
)  # shorter = faster report generation
AGENT2_TEMPERATURE: float = _env_float("AGENT2_TEMPERATURE", 0.3, 0.0, 1.0)

# ── LLM Quality / Cache ───────────────────────────────────────────────────────
LLM_CACHE_DIR: Path = AGENT2_REPORTS_DIR / "llm_cache"
LLM_CACHE_TTL_SECONDS: int = _env_int("LLM_CACHE_TTL_SECONDS", 3600)
LLM_CACHE_ENABLED: bool = _env_bool("LLM_CACHE_ENABLED", True)
LLM_QUALITY_METRICS_ENABLED: bool = _env_bool("LLM_QUALITY_METRICS_ENABLED", True)
LLM_COT_ENABLED: bool = _env_bool("LLM_COT_ENABLED", True)
LLM_CROSS_VALIDATION: bool = _env_bool("LLM_CROSS_VALIDATION", False)
LLM_COMPLEXITY_HIGH: float = _env_float("LLM_COMPLEXITY_HIGH", 0.8, 0.0, 1.0)
LLM_COMPLEXITY_MEDIUM: float = _env_float("LLM_COMPLEXITY_MEDIUM", 0.5, 0.0, 1.0)

for _dir in [
    REPORTS_DIR,
    AGENT1_REPORTS_DIR,
    AGENT2_REPORTS_DIR,
    LLM_CACHE_DIR,
    LOG_DIR,
    CONTROL_FILE.parent,
]:
    _dir.mkdir(parents=True, exist_ok=True)

TZ: str = _env_str("TZ", "UTC")
if TZ:
    os.environ.setdefault("TZ", TZ)

DEBUG: bool = _env_bool("AGENT2_DEBUG", False)
LOG_LEVEL: str = _env_str("LOG_LEVEL", "INFO")
PARALLEL_WORKERS: int = max(1, (os.cpu_count() or 2) - 1)


def get_dashboard_config() -> dict[str, Any]:
    return {
        "port": PORT,
        "host": DASHBOARD_HOST,
        "theme": DASHBOARD_THEME,
        "update_interval_ms": DASHBOARD_UPDATE_INTERVAL_MS,
        "window_days": DASHBOARD_WINDOW_DAYS,
        "window_minutes": CISO_WINDOW_MINUTES,
        "backend_port": BACKEND_PORT,
        "backend_host": BACKEND_HOST,
        "agent2_poll_seconds": AGENT2_POLL_SECONDS,
        "llm_provider": LLM_PROVIDER,
        "confirmation_threshold": CONFIRMATION_THRESHOLD,
        "max_hypotheses": PROBABILISTIC_MAX_HYPOTHESES,
        "decision_timeout_seconds": CISO_DECISION_TIMEOUT_SECONDS,
        "texer_port": TEXER_PORT,
        "texer_host": TEXER_HOST,
        "window_mode": WINDOW_MODE,
    }


def get_agent_timing_config() -> dict[str, Any]:
    return {
        "window_hours": WINDOW_HOURS,
        "step_hours": STEP_HOURS,
        "default_window_days": DASHBOARD_WINDOW_DAYS,
        "default_window_seconds": DEFAULT_WINDOW_SECONDS,
        "default_window_ms": DEFAULT_WINDOW_MS,
        "stream_timeout_minutes": STREAM_TIMEOUT_MINUTES,
        "stream_step_minutes": STREAM_STEP_MINUTES,
        "agent2_poll_seconds": AGENT2_POLL_SECONDS,
        "agent2_run_once": AGENT2_RUN_ONCE,
        "ciso_window_minutes": CISO_WINDOW_MINUTES,
        "ciso_window_lookback": CISO_WINDOW_LOOKBACK,
        "ciso_window_forward": CISO_WINDOW_FORWARD,
        "ciso_min_alerts_per_window": CISO_MIN_ALERTS_PER_WINDOW,
        "ciso_decision_timeout_seconds": CISO_DECISION_TIMEOUT_SECONDS,
        "trigger_on_window_expiry": TRIGGER_ON_WINDOW_EXPIRY,
        "trigger_expiry_buffer_seconds": TRIGGER_EXPIRY_BUFFER_SECONDS,
        "window_overlap_ratio": WINDOW_OVERLAP_RATIO,
        "confirmation_threshold": CONFIRMATION_THRESHOLD,
        "max_hypotheses": PROBABILISTIC_MAX_HYPOTHESES,
    }


def get_ciso_config() -> dict[str, Any]:
    return {
        "window_minutes": CISO_WINDOW_MINUTES,
        "lookback": CISO_WINDOW_LOOKBACK,
        "forward": CISO_WINDOW_FORWARD,
        "min_alerts": CISO_MIN_ALERTS_PER_WINDOW,
        "trigger_on_expiry": TRIGGER_ON_WINDOW_EXPIRY,
        "expiry_buffer_seconds": TRIGGER_EXPIRY_BUFFER_SECONDS,
        "overlap_ratio": WINDOW_OVERLAP_RATIO,
        "decision_timeout_seconds": CISO_DECISION_TIMEOUT_SECONDS,
        "decision_enabled": CISO_DECISION_ENABLED,
        "confirmation_threshold": CONFIRMATION_THRESHOLD,
        "max_hypotheses": PROBABILISTIC_MAX_HYPOTHESES,
    }


def get_graph_config() -> dict[str, Any]:
    return {
        "decay_hours": HYPOTHESIS_DECAY_HOURS,
        "confirmation_threshold": CONFIRMATION_THRESHOLD,
        "max_hypotheses_per_node": MAX_HYPOTHESES_PER_NODE,
        "convergence_std_threshold": CONVERGENCE_STD_THRESHOLD,
        "incoherence_threshold": INCOHERENCE_THRESHOLD,
        "max_parallel_windows": MAX_PARALLEL_WINDOWS,
    }


def print_config() -> None:
    _config_logger.info("─" * 60)
    _config_logger.info("Active configuration")
    _config_logger.info(f"  PROJECT_ROOT: {PROJECT_ROOT}")
    _config_logger.info(f"  PORT: {PORT}")
    _config_logger.info(f"  DASHBOARD_HOST: {DASHBOARD_HOST}")
    _config_logger.info(f"  BACKEND_PORT: {BACKEND_PORT}")
    _config_logger.info(f"  BACKEND_HOST: {BACKEND_HOST}")
    _config_logger.info(f"  WINDOW_HOURS: {WINDOW_HOURS}")
    _config_logger.info(f"  STEP_HOURS: {STEP_HOURS}")
    _config_logger.info(f"  CISO_WINDOW_MINUTES: {CISO_WINDOW_MINUTES}")
    _config_logger.info(f"  AGENT2_POLL_SECONDS: {AGENT2_POLL_SECONDS}")
    _config_logger.info(f"  LLM_PROVIDER: {LLM_PROVIDER}")
    _config_logger.info(f"  LLM_PROVIDER2: {LLM_PROVIDER2}")
    _config_logger.info(f"  CONFIRMATION_THRESHOLD: {CONFIRMATION_THRESHOLD}")
    _config_logger.info(f"  TEXER_HOST: {TEXER_HOST}  TEXER_PORT: {TEXER_PORT}")
    _config_logger.info(
        f"  TEXER_COMPILE_TIMEOUT: {TEXER_COMPILE_TIMEOUT}s  RUNS: {TEXER_COMPILE_RUNS}"
    )
    _config_logger.info(
        f"  AGENT2_MAX_TOKENS: {AGENT2_MAX_TOKENS}  TEMPERATURE: {AGENT2_TEMPERATURE}"
    )
    _config_logger.info("─" * 60)


if __name__ == "__main__":
    print_config()
