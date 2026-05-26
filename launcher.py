"""
SOC/CISO Dashboard Launcher - Inicia todos os serviços.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE

if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env BEFORE importing shared_config — all modules share sys.modules cache,
# so shared_config._load_env_file() only runs once. Loading here with override=True
# guarantees the .env values are in os.environ before any module reads them.
_env_file = _PROJECT_ROOT / ".env"
if _env_file.exists():
  try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(_env_file, override=True)
  except ImportError:
    with open(_env_file, encoding="utf-8") as _fh:
      for _line in _fh:
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
          continue
        _k, _, _v = _line.partition("=")
        _v = _v.split("#")[0].strip().strip('"').strip("'")
        if _k.strip():
          os.environ[_k.strip()] = _v

try:
  from shared_config import (
    PORT,
    DASHBOARD_HOST,
    BACKEND_PORT,
    BACKEND_HOST,
    BACKEND_WORKERS,
    BACKEND_LOG_LEVEL,
    PROJECT_ROOT,
    AGENT1_REPORTS_DIR,
    AGENT2_REPORTS_DIR,
    CONTROL_FILE,
    AGENT2_POLL_SECONDS,
    AGENT2_RUN_ONCE,
  )
except ImportError as e:
  print(f"[WARNING] Could not import shared_config: {e}")
  PORT = 5001
  DASHBOARD_HOST = "localhost"
  BACKEND_PORT = 8000
  BACKEND_HOST = "127.0.0.1"
  BACKEND_WORKERS = 1
  BACKEND_LOG_LEVEL = "warning"
  PROJECT_ROOT = _PROJECT_ROOT
  AGENT1_REPORTS_DIR = PROJECT_ROOT / "reports" / "agent1"
  AGENT2_REPORTS_DIR = PROJECT_ROOT / "reports" / "agent2"
  CONTROL_FILE = PROJECT_ROOT / "reports" / "control" / "window_request.json"
  AGENT2_POLL_SECONDS = 5

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_logger(name):
  return logging.getLogger(name)

logger = get_logger(__name__)

SOC_DASHBOARD_DIR = PROJECT_ROOT / "soc-dashboard"
FRONTEND_DIST_DIR = SOC_DASHBOARD_DIR / "frontend" / "dist"
SSE_SERVER_DIR = SOC_DASHBOARD_DIR / "server"
BACKEND_DIR = SOC_DASHBOARD_DIR / "backend"

NO_BROWSER = "--no-browser" in sys.argv
AGENT1_ONLY = "--agent1-only" in sys.argv
AGENT2_ONLY = "--agent2-only" in sys.argv

__version__ = "4.2.0"

def _ensure_directories() -> None:
  dirs_to_create = [
    PROJECT_ROOT / "logs",
    PROJECT_ROOT / "reports",
    AGENT1_REPORTS_DIR,
    AGENT2_REPORTS_DIR,
    PROJECT_ROOT / "reports" / "control",
  ]
  for d in dirs_to_create:
    d.mkdir(parents=True, exist_ok=True)
  logger.info("Directories verified/created")

def _check_node_npm() -> bool:
  import shutil
  node_path = shutil.which("node")
  npm_path = shutil.which("npm")

  if not node_path:
    logger.error("Node.js is not installed or not in PATH")
    return False
  if not npm_path:
    logger.error("npm is not installed or not in PATH")
    return False
  return True

def _build_frontend() -> bool:
  if FRONTEND_DIST_DIR.exists() and any(FRONTEND_DIST_DIR.iterdir()):
    logger.info("Frontend dist already built: %s", FRONTEND_DIST_DIR)
    return True

  frontend_src = SOC_DASHBOARD_DIR / "frontend"
  if not frontend_src.exists():
    logger.error("Frontend source not found: %s", frontend_src)
    return False

  if not _check_node_npm():
    return False

  logger.info("Frontend dist not found — running npm install and build...")
  npm = "npm.cmd" if sys.platform == "win32" else "npm"

  try:
    if not (frontend_src / "node_modules").exists():
      logger.info("Installing dependencies...")
      result = subprocess.run(
        [npm, "install", "--silent", "--no-fund"],
        cwd=frontend_src,
        capture_output=True,
        text=True,
        timeout=300,
      )
      if result.returncode != 0:
        logger.error("npm install failed: %s", result.stderr[:500])
        return False
      logger.info("Dependencies installed")

    logger.info("Building dashboard...")
    result = subprocess.run(
      [npm, "run", "build", "--silent"],
      cwd=frontend_src,
      capture_output=True,
      text=True,
      timeout=300,
    )
    if result.returncode == 0:
      logger.info("Frontend build succeeded.")
      return True
    else:
      logger.error("Frontend build failed (exit %d):\n%s", result.returncode, result.stderr[-2000:])
      return False
  except subprocess.TimeoutExpired:
    logger.error("Frontend build timed out after 300s")
    return False
  except Exception as exc:
    logger.error("Frontend build error: %s", exc)
    return False

def _check_python_packages() -> bool:
  required = ["fastapi", "uvicorn"]
  missing = []

  for pkg in required:
    try:
      __import__(pkg)
    except ImportError:
      missing.append(pkg)

  if missing:
    logger.error(f"Missing Python packages: {', '.join(missing)}")
    logger.error(f"Install with: pip install {' '.join(missing)}")
    return False
  return True

def _http_wait(url: str, label: str, retries: int = 30, interval: float = 0.5) -> bool:
  import urllib.request
  import urllib.error

  for i in range(retries):
    try:
      urllib.request.urlopen(url, timeout=3)
      logger.info(f"{label} ready at {url}")
      return True
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
      if i < retries - 1:
        time.sleep(interval)
  logger.warning(f"{label} not responding at {url}")
  return False

def _find_agent1() -> Optional[Path]:
  main_path = PROJECT_ROOT / "agent1" / "main.py"
  if main_path.exists():
    logger.info(f"Found Agent 1 at: {main_path}")
    return main_path
  logger.error(f"Agent 1 not found. Searched in: {PROJECT_ROOT / 'agent1' / 'main.py'}")
  return None

def _find_agent2() -> Optional[Path]:
  graph_reporter = PROJECT_ROOT / "agent2" / "graph_reporter.py"
  if graph_reporter.exists():
    logger.info(f"Found Agent 2 (Graph Reporter) at: {graph_reporter}")
    return graph_reporter
  logger.error("Agent 2 not found")
  return None

class ServiceLauncher:
  def __init__(self):
    self.processes: dict[str, subprocess.Popen] = {}
    self.threads: dict[str, threading.Thread] = {}
    # self._shutdown_event = threading.Event()

  def start_backend(self) -> bool:
    backend_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"

    if _http_wait(backend_url, "Backend", retries=2, interval=0.2):
      logger.info("Backend already running")
      return True

    if not BACKEND_DIR.exists():
      logger.error("Backend directory not found: %s", BACKEND_DIR)
      BACKEND_DIR.mkdir(parents=True, exist_ok=True)
      app_dir = BACKEND_DIR / "app"
      app_dir.mkdir(parents=True, exist_ok=True)
      main_py = app_dir / "main.py"
      if not main_py.exists():
        main_py.write_text('')

    logger.info("Starting FastAPI backend on %s:%d...", BACKEND_HOST, BACKEND_PORT)

    cmd = [
      sys.executable, "-m", "uvicorn",
      "app.main:app",
      "--host", BACKEND_HOST,
      "--port", str(BACKEND_PORT),
      "--workers", str(BACKEND_WORKERS),
      "--log-level", BACKEND_LOG_LEVEL,
    ]

    try:
      process = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
      )
      self.processes["backend"] = process
      self._pipe_logs(process, "backend")

      if _http_wait(backend_url, "Backend", retries=30, interval=0.5):
        logger.info("Backend ready at http://%s:%d", BACKEND_HOST, BACKEND_PORT)
        return True
      else:
        logger.error("Backend failed to start")
        return False
    except Exception as exc:
      logger.error("Failed to start backend: %s", exc)
      return False

  def start_sse_server(self) -> bool:
    sse_url = f"http://{DASHBOARD_HOST}:{PORT}/health"

    if _http_wait(sse_url, "SSE server", retries=2, interval=0.2):
      logger.info("SSE server already running")
      return True

    sse_script = SSE_SERVER_DIR / "sse_server.py"
    if not sse_script.exists():
      logger.error("SSE server script not found: %s", sse_script)
      return False

    logger.info("Starting SSE server on port %d...", PORT)

    cmd = [sys.executable, str(sse_script)]

    try:
      process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
      )
      self.processes["sse"] = process
      self._pipe_logs(process, "sse")

      if _http_wait(sse_url, "SSE server", retries=30, interval=0.5):
        logger.info("SSE server ready at http://%s:%d", DASHBOARD_HOST, PORT)
        return True
      else:
        logger.error("SSE server failed to start")
        return False
    except Exception as exc:
      logger.error("Failed to start SSE server: %s", exc)
      return False

  def start_texer(self) -> bool:
    """Start the LaTeX→PDF rendering server (server_texer.py)."""
    try:
      from shared_config import TEXER_PORT, TEXER_HOST
    except ImportError:
      TEXER_PORT, TEXER_HOST = 5002, "localhost"

    texer_url = f"http://{TEXER_HOST}:{TEXER_PORT}/health"

    if _http_wait(texer_url, "Texer", retries=2, interval=0.2):
      logger.info("Texer already running at %s", texer_url)
      return True

    texer_script = SSE_SERVER_DIR / "server_texer.py"
    if not texer_script.exists():
      logger.warning("server_texer.py not found at %s — PDF rendering disabled", texer_script)
      return False

    # Check flask is available before attempting to start
    try:
      import flask  # noqa: F401
    except ImportError:
      logger.warning(
        "flask not installed — Texer cannot start. "
        "Install with: pip install flask flask-cors"
      )
      return False

    logger.info("Starting Texer on port %d...", TEXER_PORT)
    try:
      # Pass AGENT2_REPORTS_DIR explicitly so texer finds the .tex files
      # regardless of its own _PROJECT_ROOT calculation
      texer_env = os.environ.copy()
      try:
        from shared_config import AGENT2_REPORTS_DIR as _a2dir
        texer_env["AGENT2_REPORTS_DIR"] = str(_a2dir)
      except ImportError:
        pass
      process = subprocess.Popen(
        [sys.executable, str(texer_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=texer_env,
        # Windows: don't create a new console window
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
      )
      self.processes["texer"] = process
      self._pipe_logs(process, "texer")

      if _http_wait(texer_url, "Texer", retries=20, interval=0.5):
        logger.info("Texer ready at http://%s:%d", TEXER_HOST, TEXER_PORT)
        return True
      else:
        logger.warning("Texer did not start in time — PDF rendering may fail")
        return False
    except Exception as exc:
      logger.error("Failed to start Texer: %s", exc)
      return False

  def start_agent1(self, agent1_path: Path) -> Optional[threading.Thread]:
    logger.info("Starting Agent 1 from %s", agent1_path.name)

    def _run():
      try:
        if str(PROJECT_ROOT) not in sys.path:
          sys.path.insert(0, str(PROJECT_ROOT))

        spec = importlib.util.spec_from_file_location("agent1_main", agent1_path)
        if spec and spec.loader:
          mod = importlib.util.module_from_spec(spec)
          spec.loader.exec_module(mod)
          if hasattr(mod, "main"):
            mod.main()
          elif hasattr(mod, "run_streaming_mode"):
            mod.run_streaming_mode()
          else:
            logger.error("Agent 1 module has no main() or run_streaming_mode()")
        else:
          logger.error("Could not load Agent 1 module")
      except Exception as exc:
        logger.error("Agent 1 error: %s", exc)
        import traceback
        traceback.print_exc()
      finally:
        logger.info("Agent 1 finished")

    thread = threading.Thread(target=_run, daemon=True, name="agent1")
    thread.start()
    self.threads["agent1"] = thread
    return thread

  def start_agent2(self, agent2_path: Path) -> Optional[threading.Thread]:
    logger.info("Starting Agent 2 from %s", agent2_path.name)

    def _run():
      try:
        if str(PROJECT_ROOT) not in sys.path:
          sys.path.insert(0, str(PROJECT_ROOT))

        spec = importlib.util.spec_from_file_location("agent2_main", agent2_path)
        if spec and spec.loader:
          mod = importlib.util.module_from_spec(spec)
          spec.loader.exec_module(mod)

          if hasattr(mod, "main"):
            mod.main()
          elif hasattr(mod, "run"):
            mod.run()
          else:
            logger.error(f"Agent 2 module {agent2_path.name} has no main() or run()")
        else:
          logger.error("Could not load Agent 2 module")
      except Exception as exc:
        logger.error("Agent 2 error: %s", exc)
        import traceback
        traceback.print_exc()

    thread = threading.Thread(target=_run, daemon=True, name="agent2")
    thread.start()
    self.threads["agent2"] = thread
    return thread

  def _pipe_logs(self, process: subprocess.Popen, name: str) -> None:
    def _pipe():
      while process.poll() is None:
        try:
          line = process.stdout.readline()
          if line:
            line_clean = line.rstrip()
            if line_clean and not line_clean.startswith("Debug:"):
              logger.debug("[%s] %s", name, line_clean)
        except Exception:
          break

    threading.Thread(target=_pipe, daemon=True, name=f"pipe-{name}").start()

  def open_browser(self) -> None:
    if not NO_BROWSER:
      try:
        webbrowser.open(f"http://{DASHBOARD_HOST}:{PORT}")
        logger.info("Browser opened -> http://%s:%d", DASHBOARD_HOST, PORT)
      except Exception as exc:
        logger.warning("Could not open browser: %s", exc)

  def shutdown(self) -> None:
    logger.info("Shutting down services...")
    for name, process in self.processes.items():
      if process and process.poll() is None:
        logger.info("Stopping %s...", name)
        process.terminate()
        try:
          process.wait(timeout=5)
        except subprocess.TimeoutExpired:
          process.kill()
    self.processes.clear()
    self.threads.clear()
    logger.info("Shutdown complete.")

async def main() -> None:
  input_file = PROJECT_ROOT / "projD.txt"
  if not input_file.exists():
    logger.error("projD.txt not found in %s", PROJECT_ROOT)
    sys.exit(1)

  _ensure_directories()

  agent1_path = _find_agent1() if not AGENT2_ONLY else None
  agent2_path = _find_agent2() if not AGENT1_ONLY else None

  if not AGENT2_ONLY and not agent1_path:
    logger.error("Agent 1 not found")
    sys.exit(1)

  if not AGENT1_ONLY and not AGENT2_ONLY and not agent2_path:
    logger.warning("Agent 2 not found - continuing without it")

  if not AGENT1_ONLY and not AGENT2_ONLY:
    if not _check_python_packages():
      logger.warning("Some Python packages missing - backend may not work")

  # ── Read active configuration for banner ─────────────────────────────────
  try:
    from shared_config import (
      WINDOW_MODE, CISO_WINDOW_MINUTES, CONFIRMATION_THRESHOLD,
      CISO_DECISION_TIMEOUT_SECONDS, PROBABILISTIC_MAX_HYPOTHESES,
      LLM_PROVIDER, LLM_PROVIDER2, OLLAMA_MODEL, ANTHROPIC_MODEL,
      AGENT2_TIMEOUT_SECONDS, AGENT2_MAX_TOKENS, AGENT2_POLL_SECONDS,
      TEXER_PORT, TEXER_HOST,
    )
    _llm_agent2 = (
      f"ollama/{OLLAMA_MODEL}" if LLM_PROVIDER2 == "ollama"
      else f"anthropic/{ANTHROPIC_MODEL}" if LLM_PROVIDER2 == "anthropic"
      else LLM_PROVIDER2 if LLM_PROVIDER2 != "none" else "none (rule-based)"
    )
  except Exception:
    WINDOW_MODE = os.environ.get("WINDOW_MODE", "fixed")
    CISO_WINDOW_MINUTES = "?"
    CONFIRMATION_THRESHOLD = "?"
    CISO_DECISION_TIMEOUT_SECONDS = "?"
    PROBABILISTIC_MAX_HYPOTHESES = "?"
    _llm_agent2 = "?"
    AGENT2_TIMEOUT_SECONDS = "?"
    AGENT2_MAX_TOKENS = "?"
    AGENT2_POLL_SECONDS = "?"
    TEXER_PORT = 5002
    TEXER_HOST = "localhost"

  banner = (
    f"SOC/CISO Dashboard Launcher v{__version__}\n"
    f"\n"
    f"  SERVIÇOS\n"
    f"  ─────────────────────────────────────────\n"
    f"  Dashboard  : http://{DASHBOARD_HOST}:{PORT}\n"
    f"  Backend    : http://{BACKEND_HOST}:{BACKEND_PORT}\n"
    f"  Texer/LaTeX: http://{TEXER_HOST}:{TEXER_PORT}\n"
    f"  Project    : {PROJECT_ROOT}\n"
    f"  Mode       : {'agent1-only' if AGENT1_ONLY else 'agent2-only' if AGENT2_ONLY else 'full'}\n"
    f"\n"
    f"  AGENTE 1 (Classificação ENISA→CISO)\n"
    f"  ─────────────────────────────────────────\n"
    f"  Agent 1    : {agent1_path.name if agent1_path else 'not found'}\n"
    f"  Window mode: {WINDOW_MODE}\n"
    + (
    f"  Window dur : {CISO_WINDOW_MINUTES} min (fixo para todos os alertas)\n"
    if WINDOW_MODE == "fixed" else
    f"  Window dur : variável por fase trigger:\n"
    f"               RECON=5m · INITIAL_ACCESS=10m · EXECUTION=15m\n"
    f"               PERSISTENCE=15m · LATERAL_MOVEMENT=20m\n"
    f"               EXFILTRATION=25m · IMPACT=30m\n"
    f"               (+ extensão de 5m por alerta adicional, hard cap 60m)\n"
    ) +
    f"  Convergence: {CONFIRMATION_THRESHOLD} (auto-confirm threshold)\n"
    f"  Oper.timeout: {CISO_DECISION_TIMEOUT_SECONDS}s (confirm manual)\n"
    f"  Max hyp.   : {PROBABILISTIC_MAX_HYPOTHESES} opções CISO por janela\n"
    f"\n"
    f"  AGENTE 2 (Relatórios LLM)\n"
    f"  ─────────────────────────────────────────\n"
    f"  Agent 2    : Graph Reporter (trigger-based)\n"
    f"  LLM Agente1: none (rule-based — sem LLM)\n"
    f"  LLM Agente2: {_llm_agent2}\n"
    f"  LLM timeout: {AGENT2_TIMEOUT_SECONDS}s\n"
    f"  Max tokens : {AGENT2_MAX_TOKENS}\n"
    f"  Poll interv: {AGENT2_POLL_SECONDS}s\n"
  )
  print("\n" + "=" * 60)
  print(banner)
  print("=" * 60 + "\n")

  launcher = ServiceLauncher()

  def signal_handler(signum, frame):
    logger.info("Received signal %d", signum)
    launcher.shutdown()
    sys.exit(0)

  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)

  sse_ok = launcher.start_sse_server()
  if not sse_ok:
    logger.error("SSE server failed to start - cannot proceed")
    sys.exit(1)

  # Start LaTeX rendering server (non-fatal if missing pdflatex)
  launcher.start_texer()

  if not AGENT2_ONLY and not AGENT1_ONLY:
    if not _build_frontend():
      logger.error("Cannot start dashboard without built frontend")
      logger.info("Continuing with agents only...")
    else:
      backend_ok = launcher.start_backend()
      if not backend_ok:
        logger.warning("Backend not available - some features may be limited")
      launcher.open_browser()

  if not AGENT2_ONLY and agent1_path:
    time.sleep(2)
    launcher.start_agent1(agent1_path)
    logger.info("Agent 1 started")

  if not AGENT1_ONLY and agent2_path:
    time.sleep(3)
    launcher.start_agent2(agent2_path)
    logger.info("Agent 2 started")

  try:
    while True:
      await asyncio.sleep(1)
  except KeyboardInterrupt:
    logger.info("Ctrl-C received")
    launcher.shutdown()

if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user")
    sys.exit(0)
  except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
