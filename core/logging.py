"""
Logging configuration for the entire system.
"""

from __future__ import annotations

import logging
import sys
import os
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent

if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

try:
  from shared_config import LOG_DIR, DEBUG as AGENT2_DEBUG_FLAG
except ImportError:
  LOG_DIR = _PROJECT_ROOT / "logs"
  AGENT2_DEBUG_FLAG = False

PERFORMANCE_LEVEL: int = 25
EXECUTION_LEVEL: int = 15

logging.addLevelName(PERFORMANCE_LEVEL, "PERFORMANCE")
logging.addLevelName(EXECUTION_LEVEL, "EXECUTION")

_CONSOLE_FMT = logging.Formatter(
  fmt="%(asctime)s [%(levelname)-11s] [%(name)s] %(message)s",
  datefmt="%Y-%m-%d %H:%M:%S",
)

_FILE_FMT = logging.Formatter(
  fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
  datefmt="%Y-%m-%d %H:%M:%S",
)

_ERROR_FMT = logging.Formatter(
  fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s\n%(exc_info)s",
  datefmt="%Y-%m-%d %H:%M:%S",
)

_handlers: dict[str, logging.Handler] = {}

def _get_log_file_path(name: str) -> Optional[Path]:
  LOG_DIR.mkdir(parents=True, exist_ok=True)
  lower = name.lower()

  if "agent2" in lower:
    return LOG_DIR / "agent2.log"
  if "agent1" in lower:
    return LOG_DIR / "agent1.log"
  if "execution" in lower:
    return LOG_DIR / "execution.log"
  if "classification" in lower:
    return LOG_DIR / "classification.log"
  if "performance" in lower:
    return LOG_DIR / "performance.log"
  if "backend" in lower:
    return LOG_DIR / "backend.log"
  if "sse" in lower:
    return LOG_DIR / "sse.log"

  return LOG_DIR / "app.log"

def _make_file_handler(path: Path, level: int, formatter: logging.Formatter) -> logging.FileHandler:
  key = str(path)
  if key not in _handlers:
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    _handlers[key] = fh
  return _handlers[key]

def _console_handler() -> logging.StreamHandler:
  key = "__console__"
  if key not in _handlers:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(_CONSOLE_FMT)
    _handlers[key] = ch
  return _handlers[key]

def _error_file_handler() -> logging.FileHandler:
  error_log = LOG_DIR / "errors.log"
  return _make_file_handler(error_log, logging.ERROR, _ERROR_FMT)

def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
  logger = logging.getLogger(name)

  if logger.handlers:
    return logger

  logger.setLevel(level)
  logger.propagate = False

  logger.addHandler(_console_handler())

  log_file = _get_log_file_path(name)
  if log_file:
    file_level = logging.DEBUG if AGENT2_DEBUG_FLAG else logging.INFO
    file_handler = _make_file_handler(log_file, file_level, _FILE_FMT)
    logger.addHandler(file_handler)

  logger.addHandler(_error_file_handler())

  if name in ["execution", "classification", "performance"] or "agent" in name:
    logger.debug(f"Logger initialized: {name}")

  return logger

def _configure_external_logging() -> None:
  if os.getenv("LOG_LEVEL", "").upper() != "DEBUG":
    for lib in ["httpx", "httpcore", "urllib3", "requests", "watchfiles"]:
      logging.getLogger(lib).setLevel(logging.WARNING)

_configure_external_logging()

execution_logger = get_logger("execution")
classification_logger = get_logger("classification")
performance_logger = get_logger("performance")
error_logger = get_logger("errors")

logging.getLogger("txt_logger.execution").parent = execution_logger
logging.getLogger("txt_logger.classification").parent = classification_logger
logging.getLogger("txt_logger.performance").parent = performance_logger
logging.getLogger("txt_logger.errors").parent = error_logger

if __name__ == "__main__":
  test_logger = get_logger("test")
  test_logger.info("Testing logging system...")
  print(f"\n[OK] Logging system working. Check logs directory: {LOG_DIR}")
