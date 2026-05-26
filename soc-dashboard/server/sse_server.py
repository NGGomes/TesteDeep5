from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Callable, Optional

_SERVER_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SERVER_DIR.parent.parent

if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

from core.logging import get_logger
from shared_config import AGENT2_REPORTS_DIR, AGENT1_REPORTS_DIR, CONFIRMATION_THRESHOLD, FRONTEND_DIST_DIR, PORT as _CFG_PORT, DASHBOARD_HOST as _CFG_HOST

logger = get_logger(__name__)

HOST: str = _CFG_HOST
PORT: int = _CFG_PORT
MAX_HISTORY: int = 500
PING_INTERVAL: int = 5
STATIC_DIR: Path = FRONTEND_DIST_DIR

_event_bus: dict[int, queue.Queue] = {}
_bus_lock = threading.Lock()
_alert_history: list[str] = []
_history_lock = threading.Lock()
_total_received = 0
_sent_alerts: set = set()

_agent1_callback_url: Optional[str] = None
_agent1_alerts: list[dict] = []
_agent1_total_alerts = 0
_agent1_lock = threading.Lock()

_slice_lock = threading.Lock()
_active_slice = {
  "dataMinMs": 0,
  "dataMaxMs": 0,
  "windowStartMs": 0,
  "windowEndMs": 0,
  "windowStartIso": "",
  "windowEndIso": "",
}

_ping_started = False
_ping_lock = threading.Lock()

def _subscribe() -> queue.Queue:
  q = queue.Queue(maxsize=1000)
  with _history_lock:
    history_snapshot = list(_alert_history)
  for msg in history_snapshot:
    try:
      q.put_nowait(msg)
    except queue.Full:
      break
  with _bus_lock:
    _event_bus[id(q)] = q
  return q

def _unsubscribe(q: queue.Queue) -> None:
  with _bus_lock:
    _event_bus.pop(id(q), None)

_NO_HISTORY_EVENTS = frozenset({
  "next_alert_info",
  "dataset_bounds",
  "done",
  "ping",
  "alert",
  "agent1_progress",
})

def emit_event(event_type: str, payload: Any) -> None:
  global _total_received
  try:
    msg = json.dumps({"type": event_type, "payload": payload}, ensure_ascii=False)
  except Exception:
    return

  if event_type not in _NO_HISTORY_EVENTS:
    with _history_lock:
      _alert_history.append(msg)
      if len(_alert_history) > MAX_HISTORY:
        _alert_history.pop(0)

  if event_type == "alert":
    with _history_lock:
      _total_received += 1

  with _bus_lock:
    subscribers = list(_event_bus.values())

  for q in subscribers:
    try:
      q.put_nowait(msg)
    except queue.Full:
      pass

def set_agent1_alerts(alerts: list[dict], total_alerts: int) -> None:
  global _agent1_alerts, _agent1_total_alerts
  with _agent1_lock:
    _agent1_alerts = alerts
    _agent1_total_alerts = total_alerts
  logger.info(f"Agent 1 alerts set: {total_alerts} alerts loaded")

def _load_dataset_bounds() -> tuple[int, int]:
  bounds_file = AGENT1_REPORTS_DIR / "dataset_bounds.json"
  data_min_ms = 0
  data_max_ms = 0
  if bounds_file.exists():
    try:
      bounds = json.loads(bounds_file.read_text(encoding="utf-8"))
      data_min_ms = bounds.get("dataMinMs", 0)
      data_max_ms = bounds.get("dataMaxMs", 0)

      if bounds.get("alerts") and not _agent1_alerts:
        set_agent1_alerts(bounds.get("alerts"), bounds.get("total_alerts", 0))
    except Exception as e:
      logger.error(f"Failed to read bounds: {e}")
  return data_min_ms, data_max_ms

def _ensure_ping_loop() -> None:
  global _ping_started
  with _ping_lock:
    if _ping_started:
      return
    _ping_started = True

  def _ping() -> None:
    while True:
      time.sleep(PING_INTERVAL)
      emit_event("ping", {"ts": datetime.now(timezone.utc).isoformat()})

  threading.Thread(target=_ping, daemon=True, name="sse-ping").start()

_dispatched_indices: set = set()
_dispatch_lock = threading.Lock()

class _Handler(BaseHTTPRequestHandler):
  def log_message(self, fmt: str, *args: Any) -> None:
    pass

  def _send_cors(self) -> None:
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")

  def do_OPTIONS(self) -> None:
    self.send_response(204)
    self._send_cors()
    self.end_headers()

  def _serve_stream_status(self) -> None:
    self._serve_json({
      "connected_clients": len(_event_bus),
      "history_size": len(_alert_history),
      "total_received": _total_received,
      "active_slice": _active_slice,
      "agent1_alerts_loaded": _agent1_total_alerts,
      "agent1_callback_url": _agent1_callback_url,
    })

  # ========================================================================
  # NOVO: Endpoint para métricas do LLM (corrigido - agora dentro da classe)
  # ========================================================================
  def _serve_llm_metrics(self) -> None:
    """GET /api/llm/metrics - Retorna métricas de qualidade do LLM."""
    try:
      from agent2.llm_quality import get_quality_metrics, get_llm_cache
      metrics = get_quality_metrics().get_summary()
      cache_stats = get_llm_cache().stats()

      self._serve_json({
        "quality_metrics": metrics,
        "cache_stats": cache_stats,
        "llm_enabled": True,
      })
    except ImportError:
      self._serve_json({
        "error": "LLM quality metrics not available",
        "llm_enabled": False,
      })
    except Exception as e:
      self._serve_json({"error": str(e)}, status=500)

  def do_GET(self) -> None:
    path = self.path.split("?")[0]

    if path == "/events":
      self._serve_sse()
    elif path == "/api/llm/metrics":
      self._serve_llm_metrics()
    elif path == "/health":
      from shared_config import LLM_PROVIDER2, ANTHROPIC_MODEL, OLLAMA_MODEL, LITELLM_MODEL2
      provider = LLM_PROVIDER2
      if provider == "anthropic":
        model = ANTHROPIC_MODEL
      elif provider == "ollama":
        model = OLLAMA_MODEL
      else:
        model = LITELLM_MODEL2
      self._serve_json({
        "status": "ok",
        "env": "production",
        "model": model,
        "provider": provider,
        "clients": len(_event_bus),
      })
    elif path == "/slice-meta":
      data_min_ms, data_max_ms = _load_dataset_bounds()
      with _slice_lock:
        payload = dict(_active_slice)
        if data_min_ms:
          payload["dataMinMs"] = data_min_ms
        if data_max_ms:
          payload["dataMaxMs"] = data_max_ms
      self._serve_json(payload)
    elif path == "/agent2-reports":
      self._serve_agent2_reports()
    elif path == "/api/stream/status":
      self._serve_stream_status()
    elif path == "/api/config":
      self._serve_api_config()
    elif path == "/api/agent1/window-mode":
      # Read live value — os.environ may have been hot-patched by POST handler
      mode = os.environ.get("WINDOW_MODE", "fixed").strip().lower()
      if mode not in ("fixed", "adaptive"):
        mode = "fixed"
      self._serve_json({"mode": mode})
    elif path == "/render-pdf":
      self._proxy_texer_render_pdf()
    elif path.startswith("/reports/agent2/"):
      self._serve_tex_file(path)
    else:
      self._serve_static(path)

  def do_POST(self) -> None:
    path = self.path.split("?")[0]

    if path == "/ingest":
      self._handle_ingest()
    elif path == "/slice-update":
      self._handle_slice_update()
    elif path == "/api/agent2/decide":
      self._handle_agent2_decision()
    elif path == "/api/agent1/process-next":
      self._handle_next_alert()
    elif path == "/api/agent1/confirm-hypothesis":
      self._handle_confirm_hypothesis()
    elif path == "/api/agent1/finish":
      self._handle_finish()
    elif path == "/api/agent1/seek":
      self._handle_seek()
    elif path == "/api/agent1/window-mode":
      self._handle_window_mode()
    elif path == "/register-agent1":
      self._handle_register_agent1()
    else:
      self.send_response(404)
      self._send_cors()
      self.end_headers()

  def _handle_ingest(self) -> None:
    try:
      length = int(self.headers.get("Content-Length", 0))
      payload = json.loads(self.rfile.read(length))
      events = payload if isinstance(payload, list) else payload.get("events", [])
      count = 0
      for ev in events:
        etype = ev.get("type")
        epayload = ev.get("payload", {})
        
        # Enriquecer alertas com dados completos do dataset
        if etype == "alert":
            number = str(epayload.get("number") or epayload.get("Number") or "")
            if number and _agent1_alerts:
                raw = next(
                    (a for a in _agent1_alerts 
                    if str(a.get("Number") or a.get("number") or "") == number),
                    None
                )
                if raw:
                    # Merge — campos do raw têm prioridade para dados originais
                    epayload = {**epayload, **{
                        "Number":         raw.get("Number", ""),
                        "TLP":            raw.get("TLP", ""),
                        "ExternalId":     raw.get("ExternalId", ""),
                        "Priority":       raw.get("Priority", ""),
                        "Severity":       raw.get("Severity", ""),
                        "Status":         raw.get("Status", ""),
                        "Title":          raw.get("Title", ""),
                        "Source":         raw.get("Source", ""),
                        "Category":       raw.get("Category", ""),
                        "Type":           raw.get("Type", ""),
                        "Tags":           raw.get("Tags", ""),
                        "MitreAttack":    raw.get("MitreAttack", ""),
                        "AffectedAsset":  raw.get("AffectedAsset", ""),
                        "Description":    raw.get("Description", ""),
                        "UseCaseTag":     raw.get("UseCaseTag", ""),
                        "Assignee":       raw.get("Assignee", ""),
                        "IsNoiseAlert":   raw.get("IsNoiseAlert", ""),
                        "SiemDetectionTime": raw.get("SiemDetectionTime", ""),
                    }}
        if etype:
            emit_event(etype, epayload)
            count += 1
      self._serve_json({"ok": True, "emitted": count})
    except Exception as exc:
      logger.error(f"[Ingest] Error: {exc}")
      self._serve_json({"ok": False, "error": str(exc)}, status=500)

  def _handle_slice_update(self) -> None:
    try:
      length = int(self.headers.get("Content-Length", 0))
      payload = json.loads(self.rfile.read(length))
      start_ms = payload.get("windowStartMs")
      end_ms = payload.get("windowEndMs")
      start_iso = payload.get("windowStartIso", "")
      end_iso = payload.get("windowEndIso", "")

      if start_ms and end_ms:
        data_min_ms, data_max_ms = _load_dataset_bounds()
        with _slice_lock:
          _active_slice["windowStartMs"] = start_ms
          _active_slice["windowEndMs"] = end_ms
          _active_slice["windowStartIso"] = start_iso
          _active_slice["windowEndIso"] = end_iso
          _active_slice["dataMinMs"] = data_min_ms
          _active_slice["dataMaxMs"] = data_max_ms

        emit_event("slice_update", {
          "dataMinMs": data_min_ms,
          "dataMaxMs": data_max_ms,
          "windowStartMs": start_ms,
          "windowEndMs": end_ms,
          "windowStartIso": start_iso,
          "windowEndIso": end_iso,
        })
        self._serve_json({"ok": True})
      else:
        self._serve_json({"ok": False, "error": "Missing parameters"}, status=400)
    except Exception as exc:
      logger.error(f"Slice update error: {exc}")
      self.send_response(400)
      self._send_cors()
      self.end_headers()

  def _handle_agent2_decision(self) -> None:
    try:
      length = int(self.headers.get("Content-Length", 0))
      payload = json.loads(self.rfile.read(length))

      window_id = payload.get("window_id")
      decision = payload.get("decision")
      hypothesis_index = payload.get("hypothesis_index", 0)
      method = payload.get("method", "MANUAL_ANALYST")

      if not window_id or not decision:
        self._serve_json({"ok": False, "error": "Missing window_id or decision"}, status=400)
        return

      logger.info(f"[Agent2 Decision] window_id={window_id}, decision={decision}, method={method}")

      confirmed = False
      try:
        from agent1.hypothesis_graph import get_global_graph
        graph = get_global_graph()
        confirmed = graph.confirm_by_operator(window_id, decision)

        if confirmed:
          logger.info(f"[Agent2 Decision] Hypothesis '{decision}' confirmed in graph for window {window_id}")
          emit_event("decision_recorded", {
            "window_id": window_id,
            "decision": decision,
            "hypothesis_index": hypothesis_index,
            "method": method,
            "source": "graph",
            "timestamp": datetime.now(timezone.utc).isoformat(),
          })
          self._serve_json({
            "ok": True,
            "message": f"Hypothesis '{decision}' confirmed in graph",
            "source": "graph"
          })
          return
      except ImportError as e:
        logger.warning(f"Could not import HypothesisGraph: {e}")
      except Exception as e:
        logger.error(f"Error confirming via HypothesisGraph: {e}")

      decisions_dir = AGENT2_REPORTS_DIR / "decisions"
      decisions_dir.mkdir(parents=True, exist_ok=True)

      decision_data = {
        "window_id": window_id,
        "selected_hypothesis": decision,
        "hypothesis_index": hypothesis_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
      }

      decision_file = decisions_dir / f"{window_id}.json"
      decision_file.write_text(json.dumps(decision_data, indent=2), encoding="utf-8")

      emit_event("window_closed", {
        "window_id": window_id,
        "reason": "validation",
        "decision": decision,
      })

      emit_event("decision_recorded", {
        "window_id": window_id,
        "decision": decision,
        "hypothesis_index": hypothesis_index,
        "method": method,
        "source": "legacy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
      })

      self._serve_json({
        "ok": True,
        "message": "Decision recorded (legacy)",
        "source": "legacy"
      })

    except Exception as exc:
      logger.error(f"Agent2 decision error: {exc}", exc_info=True)
      self._serve_json({"ok": False, "error": str(exc)}, status=500)

  def _handle_next_alert(self) -> None:
    global _agent1_callback_url, _agent1_alerts

    try:
      content_length = int(self.headers.get("Content-Length", 0))
      payload = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
      alert_index = payload.get("alert_index", 0)

      if not _agent1_callback_url:
        self._serve_json({"ok": False, "error": "Agent 1 not registered yet"}, status=503)
        return

      if not _agent1_alerts:
        bounds_file = AGENT1_REPORTS_DIR / "dataset_bounds.json"
        if bounds_file.exists():
          try:
            bounds = json.loads(bounds_file.read_text(encoding="utf-8"))
            _agent1_alerts = bounds.get("alerts", [])
          except Exception as e:
            logger.error(f"Failed to load bounds: {e}")

      if alert_index >= len(_agent1_alerts):
        self._serve_json({"ok": False, "error": f"Index {alert_index} out of range"}, status=400)
        return

      with _dispatch_lock:
        if alert_index in _dispatched_indices:
          logger.debug(f"[next_alert] Index {alert_index} already dispatched, ignoring duplicate")
          self._serve_json({"ok": True, "message": f"Alert {alert_index} already dispatched (dedup)"})
          return
        _dispatched_indices.add(alert_index)

      alert = _agent1_alerts[alert_index]
      callback_url = _agent1_callback_url

      # Forward to agent1 in a background thread so the HTTP server thread
      # is not blocked while waiting for the agent1 callback to respond.
      def _forward():
        try:
          req = urllib.request.Request(
            callback_url,
            data=json.dumps(alert).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
          )
          with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
          logger.debug(f"[next_alert] Alert {alert_index} forwarded to agent1")
        except Exception as exc:
          logger.error(f"[next_alert] Forward failed for index {alert_index}: {exc}")
          # Remove from dispatched so the frontend can retry
          with _dispatch_lock:
            _dispatched_indices.discard(alert_index)

      threading.Thread(target=_forward, daemon=True, name=f"fwd-{alert_index}").start()
      self._serve_json({"ok": True, "message": f"Alert {alert_index} queued for forwarding"})

    except Exception as exc:
      logger.error(f"Next alert error: {exc}")
      self._serve_json({"ok": False, "error": str(exc)}, status=500)

  def _handle_register_agent1(self) -> None:
    global _agent1_callback_url

    try:
      content_length = int(self.headers.get("Content-Length", 0))

      if content_length == 0:
        self._serve_json({"ok": True, "message": "Agent 1 registration acknowledged"})
        return

      raw_body = self.rfile.read(content_length)
      body = json.loads(raw_body.decode('utf-8'))
      _agent1_callback_url = body.get("callback_url", "")
      logger.info(f"Agent 1 registered with callback URL: {_agent1_callback_url}")

      bounds_file = AGENT1_REPORTS_DIR / "dataset_bounds.json"
      if bounds_file.exists():
        try:
          bounds = json.loads(bounds_file.read_text(encoding="utf-8"))
          global _agent1_alerts
          _agent1_alerts = bounds.get("alerts", [])
        except Exception as e:
          logger.error(f"Failed to load alerts: {e}")

      self._serve_json({"ok": True, "message": "Agent 1 registration acknowledged"})

    except Exception as exc:
      logger.error(f"Register Agent1 error: {exc}")
      self._serve_json({"ok": False, "error": str(exc)}, status=500)

  def _serve_sse(self) -> None:
    self.send_response(200)
    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
    self.send_header("Cache-Control", "no-cache")
    self.send_header("X-Accel-Buffering", "no")
    self._send_cors()
    self.end_headers()

    q = _subscribe()
    logger.info(f"[SSE] New client connected. Total clients: {len(_event_bus)}")

    try:
      while True:
        try:
          data = q.get(timeout=PING_INTERVAL + 1)
          self.wfile.write(f"data: {data}\n\n".encode())
          self.wfile.flush()
        except queue.Empty:
          self.wfile.write(b": keepalive\n\n")
          self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
          return
    finally:
      _unsubscribe(q)
      logger.info(f"[SSE] Client disconnected. Total clients: {len(_event_bus)}")

  def _serve_json(self, obj: dict, status: int = 200) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode()
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self._send_cors()
    self.end_headers()
    self.wfile.write(body)

  def _serve_static(self, path: str) -> None:
    if path == "/":
      path = "/index.html"

    rel = path.lstrip("/").replace("/", os.sep)
    file_path = (STATIC_DIR / rel).resolve()

    try:
      file_path.relative_to(STATIC_DIR.resolve())
    except ValueError:
      self.send_response(403)
      self._send_cors()
      self.end_headers()
      return

    if not file_path.exists() or not file_path.is_file():
      file_path = STATIC_DIR / "index.html"
      if not file_path.exists():
        self.send_response(404)
        self._send_cors()
        self.end_headers()
        return

    mime = {
      ".html": "text/html",
      ".js": "application/javascript",
      ".css": "text/css",
    }.get(file_path.suffix, "application/octet-stream")

    body = file_path.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", mime)
    self.send_header("Content-Length", str(len(body)))
    self._send_cors()
    self.end_headers()
    self.wfile.write(body)

  def _serve_api_config(self) -> None:
    """GET /api/config — returns LLM model info and window mode for the dashboard/extension."""
    from shared_config import LLM_PROVIDER2, ANTHROPIC_MODEL, OLLAMA_MODEL, LITELLM_MODEL2, AGENT2_TIMEOUT_SECONDS
    provider = LLM_PROVIDER2
    if provider == "anthropic":
      model = ANTHROPIC_MODEL
    elif provider == "ollama":
      model = OLLAMA_MODEL
    else:
      model = LITELLM_MODEL2
    # Always read WINDOW_MODE live from os.environ — the frozen shared_config value
    # may reflect the state before .env was loaded
    live_window_mode = os.environ.get("WINDOW_MODE", "fixed").strip().lower()
    if live_window_mode not in ("fixed", "adaptive"):
      live_window_mode = "fixed"
    self._serve_json({
      "model": model,
      "active_model": model,
      "llm_provider": provider,
      "ollama_base_url": "http://localhost:11434",
      "llm_timeout_seconds": AGENT2_TIMEOUT_SECONDS,
      "api_timeout_seconds": 30,
      "window_mode": live_window_mode,
    })

  def _proxy_texer_render_pdf(self) -> None:
    """Proxy /render-pdf?file=<name_or_path> → texer on :5002/render-pdf?file=<name>."""
    import urllib.parse as _up
    import urllib.error as _ue
    qs = _up.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
    file_param = qs.get("file", [""])[0]
    if not file_param:
      self._serve_json({"error": "Missing 'file' parameter"}, status=400)
      return

    filename = Path(file_param).name
    if not filename:
      self._serve_json({"error": "Invalid file path"}, status=400)
      return

    # Normalise: always send .tex to texer (it compiles .tex → .pdf)
    tex_name = filename
    if tex_name.endswith(".pdf"):
      tex_name = tex_name[:-4] + ".tex"
    elif not tex_name.endswith(".tex"):
      tex_name += ".tex"

    try:
      from shared_config import TEXER_HOST, TEXER_PORT
    except ImportError:
      TEXER_HOST, TEXER_PORT = "localhost", 5002

    texer_url = f"http://{TEXER_HOST}:{TEXER_PORT}/render-pdf?file={_up.quote(tex_name)}"
    try:
      import urllib.request as _ur
      with _ur.urlopen(texer_url, timeout=120) as resp:
        pdf_bytes = resp.read()
      self.send_response(200)
      self.send_header("Content-Type", "application/pdf")
      self.send_header("Content-Length", str(len(pdf_bytes)))
      self.send_header("Content-Disposition", f'inline; filename="{tex_name.replace(".tex",".pdf")}"')
      self._send_cors()
      self.end_headers()
      self.wfile.write(pdf_bytes)
    except _ue.HTTPError as exc:
      # Texer responded but returned an error (e.g. 404 file not found, 500 compile error)
      try:
        body = json.loads(exc.read().decode("utf-8", errors="replace"))
        err_msg = body.get("error", str(exc))
      except Exception:
        err_msg = str(exc)
      logger.error(f"[render-pdf proxy] Texer error {exc.code}: {err_msg}")
      if exc.code == 404:
        self._serve_json({
          "error": f"Report file not found on server: {tex_name}. "
              f"The report may still be generating — try again in a few seconds.",
          "texer_url": texer_url,
        }, status=404)
      else:
        self._serve_json({"error": err_msg, "texer_url": texer_url}, status=exc.code)
    except (ConnectionRefusedError, OSError) as exc:
      msg = (f"Texer server not reachable on {TEXER_HOST}:{TEXER_PORT}. "
         f"Start it with: python soc-dashboard/server/server_texer.py")
      logger.error(f"[render-pdf proxy] Texer unreachable: {exc}")
      self._serve_json({"error": msg, "texer_url": texer_url}, status=502)
    except _ue.URLError as exc:
      # URLError wraps ConnectionRefusedError but also timeouts
      reason = str(exc.reason)
      if "refused" in reason.lower() or "connect" in reason.lower():
        msg = (f"Texer server not reachable on {TEXER_HOST}:{TEXER_PORT}. "
           f"Start it with: python soc-dashboard/server/server_texer.py")
      elif "timed out" in reason.lower():
        msg = f"Texer compile timeout — PDF may be too complex. Try again."
      else:
        msg = f"Texer error: {reason}"
      logger.error(f"[render-pdf proxy] {exc}")
      self._serve_json({"error": msg, "texer_url": texer_url}, status=502)
    except Exception as exc:
      logger.error(f"[render-pdf proxy] Unexpected: {exc}")
      self._serve_json({"error": str(exc)}, status=500)

  def _serve_tex_file(self, path: str) -> None:
    """Serve raw .tex source from AGENT2_REPORTS_DIR."""
    filename = Path(path.lstrip("/")).name  # strip /reports/agent2/
    tex_path = AGENT2_REPORTS_DIR / filename
    if not tex_path.exists() or not filename.endswith(".tex"):
      self._serve_json({"error": f"Not found: {filename}"}, status=404)
      return
    try:
      content = tex_path.read_bytes()
      self.send_response(200)
      self.send_header("Content-Type", "text/plain; charset=utf-8")
      self.send_header("Content-Length", str(len(content)))
      self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
      self._send_cors()
      self.end_headers()
      self.wfile.write(content)
    except Exception as exc:
      logger.error(f"[tex-serve] {exc}")
      self._serve_json({"error": str(exc)}, status=500)

  def _handle_window_mode(self) -> None:
    """POST /api/agent1/window-mode {mode: 'fixed'|'adaptive'}"""
    try:
      length = int(self.headers.get("Content-Length", 0))
      body = json.loads(self.rfile.read(length)) if length else {}
      mode = body.get("mode", "fixed").lower().strip()
      if mode not in ("fixed", "adaptive"):
        self._serve_json({"error": "mode must be 'fixed' or 'adaptive'"}, status=400)
        return

      import os as _os
      _os.environ["WINDOW_MODE"] = mode

      try:
        import agent1.window_manager as _wm
        _wm._WINDOW_MODE = mode
        logger.info(f"[window-mode] Switched to: {mode}")
      except Exception as exc:
        logger.warning(f"[window-mode] Hot-patch failed: {exc}")

      emit_event("window_mode_changed", {"mode": mode})
      self._serve_json({"ok": True, "mode": mode})
    except Exception as exc:
      logger.error(f"[window-mode] {exc}")
      self._serve_json({"error": str(exc)}, status=500)

  def _handle_seek(self) -> None:
    """POST /api/agent1/seek {start_ms, end_ms}"""
    global _dispatched_indices, _agent1_alerts
    try:
      length = int(self.headers.get("Content-Length", 0))
      body = json.loads(self.rfile.read(length)) if length else {}
      start_ms = int(body.get("start_ms", 0))
      end_ms = int(body.get("end_ms", 0))

      if not start_ms or not end_ms or start_ms >= end_ms:
        self._serve_json({"error": "Invalid seek range"}, status=400)
        return

      with _dispatch_lock:
        _dispatched_indices.clear()

      alerts_in_range = [
        a for a in (_agent1_alerts or [])
        if start_ms <= int(a.get("_timestamp_ms", 0)) <= end_ms
      ]

      logger.info(
        f"[seek] Reset dispatch. Range: {start_ms}→{end_ms}. "
        f"Alerts in range: {len(alerts_in_range)}/{len(_agent1_alerts or [])}"
      )

      if not alerts_in_range:
        self._serve_json({"ok": True, "alerts_in_range": 0,
                 "message": "No alerts in range — streaming will be empty"})
        return

      first = alerts_in_range[0]
      second = alerts_in_range[1] if len(alerts_in_range) > 1 else None

      emit_event("dataset_bounds", {
        "dataMinMs": start_ms,
        "dataMaxMs": end_ms,
        "total_alerts": len(alerts_in_range),
        "speed_factor": 0.5,
        "seek": True,
        "window_mode": os.environ.get("WINDOW_MODE", "fixed").strip().lower(),
        "first_alert": {
          "index": 0,
          "number": first.get("Number", ""),
          "category": first.get("Category", ""),
          "type": first.get("Type", ""),
          "timestamp_ms": first.get("_timestamp_ms", start_ms),
        },
        "second_alert": {
          "index": 1,
          "number": second.get("Number", "") if second else "",
          "category": second.get("Category", "") if second else "",
          "type": second.get("Type", "") if second else "",
          "timestamp_ms": second.get("_timestamp_ms", 0) if second else 0,
        } if second else None,
      })

      _agent1_alerts = alerts_in_range

      self._serve_json({"ok": True, "alerts_in_range": len(alerts_in_range)})

    except Exception as exc:
      logger.error(f"[seek] {exc}")
      self._serve_json({"error": str(exc)}, status=500)

  def _handle_finish(self) -> None:
    """POST /api/agent1/finish"""
    try:
      length = int(self.headers.get("Content-Length", 0))
      body = json.loads(self.rfile.read(length)) if length else {}
      windows = body.get("windows", [])

      now_iso = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
      log_path = Path(AGENT1_REPORTS_DIR) / f"classification_log_{now_iso}.json"
      log_path.parent.mkdir(parents=True, exist_ok=True)

      log_entries = []
      for w in windows:
        window_id = w.get("window_id", "")
        top_hypothesis = w.get("top_hypothesis", "")
        probability = w.get("probability", 0)
        risk_tier = w.get("risk_tier", "—")
        alerts = w.get("alerts", [])
        phases = w.get("phases", [])

        try:
          from agent1.hypothesis_graph import get_global_graph
          graph = get_global_graph()
          if graph and top_hypothesis:
            graph.confirm_by_operator(window_id, top_hypothesis)
        except Exception as exc:
          logger.warning(f"[finish] graph confirm failed for {window_id}: {exc}")

        try:
          from agent1.window_manager import get_window_manager
          wm = get_window_manager()
          if wm:
            wm.close_window(window_id, reason="finish")
        except Exception as exc:
          logger.warning(f"[finish] window close failed for {window_id}: {exc}")

        entry = {
          "window_id": window_id,
          "classification": top_hypothesis,
          "probability": round(probability, 4),
          "risk_tier": risk_tier,
          "all_hypotheses": w.get("all_hypotheses", []),
          "phases": phases,
          "phase_score": w.get("phase_score", 0),
          "alert_count": w.get("alert_count", len(alerts)),
          "created_at_ms": w.get("created_at_ms", 0),
          "expires_at_ms": w.get("expires_at_ms", 0),
          "alerts": [
            {
              "number": a.get("number", ""),
              "category": a.get("category", ""),
              "phase": a.get("phase", ""),
              "severity": a.get("severity", ""),
              "ts": a.get("ts", ""),
            }
            for a in alerts
          ],
          "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        log_entries.append(entry)
        emit_event("hypothesis_confirmed", {
          "label": top_hypothesis,
          "score": probability,
          "risk_tier": risk_tier,
          "method": "finish",
          "window_id": window_id,
        })

      log_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_windows": len(log_entries),
        "summary": {
          cat: sum(1 for e in log_entries if e["classification"] == cat)
          for cat in sorted({e["classification"] for e in log_entries})
        },
        "classifications": log_entries,
      }
      log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
      logger.info(f"[finish] Classification log written: {log_path}")

      summary_lines = [f"  • {v}× {k}" for k, v in log_data["summary"].items()]
      summary = f"{len(log_entries)} janelas processadas:\n" + "\n".join(summary_lines)

      self._serve_json({
        "ok": True,
        "log_file": str(log_path),
        "summary": summary,
        "total": len(log_entries),
        "classifications": log_data["summary"],
      })

    except Exception as exc:
      logger.error(f"[finish] {exc}", exc_info=True)
      self._serve_json({"error": str(exc)}, status=500)

  def _handle_confirm_hypothesis(self) -> None:
    """POST /api/agent1/confirm-hypothesis {window_id, hypothesis_label}"""
    try:
      length = int(self.headers.get("Content-Length", 0))
      body = json.loads(self.rfile.read(length))
      window_id = body.get("window_id", "")
      label = body.get("hypothesis_label", "")
      if not window_id or not label:
        self._serve_json({"error": "Missing window_id or hypothesis_label"}, status=400)
        return

      from agent1.hypothesis_graph import get_global_graph
      graph = get_global_graph()
      confirmed = graph.confirm_by_operator(window_id, label)

      if confirmed:
        now_ms = datetime.now(timezone.utc).timestamp() * 1000

        try:
          from agent1.window_manager import get_window_manager
          wm = get_window_manager()
          if wm:
            wm.close_window(window_id, reason=f"operator:{label}")
        except Exception as exc:
          logger.warning(f"[confirm-hypothesis] window_manager close failed: {exc}")

        state = graph.get_graph_state()
        node_data = next((n for n in state.get("nodes", []) if n["label"] == label), {})
        score = node_data.get("cumulative_score", 0.8)
        tier = node_data.get("risk_tier", "HIGH")

        # Use the running GraphReporter singleton directly — it has the live graph context.
        # Supervisor fallback only if reporter isn't running.
        def _trigger_report():
          try:
            from agent2.graph_reporter import get_global_reporter
            reporter = get_global_reporter()
            if reporter:
              ok = reporter.trigger_report_now(label, score, now_ms, tier, "operator")
              if ok:
                logger.info(f"[confirm-hypothesis] Report generated via GraphReporter: {label}")
                return
              logger.warning(f"[confirm-hypothesis] GraphReporter.trigger_report_now failed — report queued for retry")
            else:
              logger.warning(f"[confirm-hypothesis] GraphReporter not running — report will be queued on next poll")
          except Exception as exc:
            logger.error(f"[confirm-hypothesis] _trigger_report failed: {exc}", exc_info=True)

        threading.Thread(target=_trigger_report, daemon=True, name="report-trigger").start()
        self._serve_json({"ok": True, "confirmed": True, "label": label})
      else:
        self._serve_json({"ok": False, "message": "Hypothesis not found in pending validations"})
    except Exception as exc:
      logger.error(f"[confirm-hypothesis] {exc}")
      self._serve_json({"error": str(exc)}, status=500)    

  def _serve_agent2_reports(self) -> None:
    reports = []
    if AGENT2_REPORTS_DIR.exists():
      for f in sorted(AGENT2_REPORTS_DIR.glob("report_*.json"), reverse=True)[:20]:
        try:
          reports.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
          pass

      for f in sorted(AGENT2_REPORTS_DIR.glob("graph_report_*.json"), reverse=True)[:20]:
        try:
          reports.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
          pass
    self._serve_json(reports)

class _ThreadingServer(ThreadingMixIn, HTTPServer):
  daemon_threads = True
  allow_reuse_address = True

def start_server(host: str = HOST, port: int = PORT) -> _ThreadingServer:
  _ensure_ping_loop()
  server = _ThreadingServer((host, port), _Handler)
  thread = threading.Thread(target=server.serve_forever, daemon=True, name="sse-server")
  thread.start()
  logger.info(f"SSE server listening on http://{host}:{port}")
  return server

def stop_server(server: _ThreadingServer) -> None:
  server.shutdown()
  logger.info("SSE server stopped")

if __name__ == "__main__":
  srv = start_server()
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    stop_server(srv)