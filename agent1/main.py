from __future__ import annotations

import json
import threading
import queue 
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable

import sys
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
 sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import (
 AGENT1_REPORTS_DIR,
 INPUT_DATA_FILE,
 CISO_WINDOW_MINUTES,
 PROBABILISTIC_MAX_HYPOTHESES,
 PORT,
 DASHBOARD_HOST,
 CONFIRMATION_THRESHOLD,
 STREAM_SPEED_FACTOR,
)
from agent1.window_manager import WindowManager, WindowEvidence, CISOOption
from agent1.hypothesis_graph import HypothesisGraph, get_global_graph, reset_global_graph
from core.logging import get_logger

_logger = get_logger("agent1.main")
_console_logger = get_logger("agent1.console")

_processed_alerts: set = set()
_window_manager: Optional[WindowManager] = None
_graph: Optional[HypothesisGraph] = None
_is_running = False
_alert_history: List[Dict] = []
_all_alerts: List[Dict] = []
_current_alert_index = 0

_alert_queue = queue.Queue()
_http_server = None

_sse_emit_queue: queue.Queue = queue.Queue()

def _sse_worker() -> None:
  """Dedicated thread that drains _sse_emit_queue and forwards events to the
  SSE server. Decouples alert processing from network I/O completely."""
  import urllib.request as _ur
  while True:
    try:
      item = _sse_emit_queue.get(timeout=5)
      if item is None:
        break
      event_type, payload = item
      try:
        url = f"http://{DASHBOARD_HOST}:{PORT}/ingest"
        body = json.dumps([{"type": event_type, "payload": payload}],
                 ensure_ascii=False, default=str).encode()
        req = _ur.Request(url, data=body,
                  headers={"Content-Type": "application/json"}, method="POST")
        with _ur.urlopen(req, timeout=2):
          pass
      except Exception as e:
        _logger.warning(f"SSE emit failed ({event_type}): {e}")
    except queue.Empty:
      continue

_sse_worker_thread: Optional[threading.Thread] = None

def _start_sse_worker() -> None:
  global _sse_worker_thread
  _sse_worker_thread = threading.Thread(target=_sse_worker, daemon=True, name="sse-worker")
  _sse_worker_thread.start()

def _emit_sse(event_type: str, payload: dict) -> bool:
  """Non-blocking SSE emit — queues the event for the dedicated SSE worker thread."""
  try:
    _sse_emit_queue.put_nowait((event_type, payload))
    return True
  except queue.Full:
    _logger.warning(f"SSE emit queue full, dropping {event_type}")
    return False

def start_http_server_for_callbacks(port: int = 8002):
 ""
 from http.server import HTTPServer, BaseHTTPRequestHandler
 
 class CallbackHandler(BaseHTTPRequestHandler):
  def log_message(self, fmt, *args):
   pass
  
  def do_POST(self):
   if self.path == "/ingest":
    try:
     content_length = int(self.headers.get("Content-Length", 0))
     body = self.rfile.read(content_length)
     alert = json.loads(body)
     
     _logger.info(f"Callback received: alert {alert.get('Number', 'unknown')}")
     _alert_queue.put(alert)
     
     self.send_response(200)
     self.send_header("Content-Type", "application/json")
     self.end_headers()
     self.wfile.write(json.dumps({"ok": True}).encode())
    except Exception as e:
     _logger.error(f"Error in callback: {e}")
     self.send_response(500)
     self.end_headers()
   else:
    self.send_response(404)
    self.end_headers()
  
  def do_GET(self):
   if self.path == "/health":
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps({"status": "ok"}).encode())
   else:
    self.send_response(404)
    self.end_headers()
 
 server = HTTPServer(("127.0.0.1", port), CallbackHandler)
 thread = threading.Thread(target=server.serve_forever, daemon=True)
 thread.start()
 _logger.info(f"Agent 1 callback server listening on port {port}")
 return server

def register_with_sse_server(callback_port: int = 8002) -> bool:
 ""
 try:
  import urllib.request
  import urllib.error
  
  time.sleep(2)
  
  url = f"http://{DASHBOARD_HOST}:{PORT}/register-agent1"
  body = json.dumps({
   "agent": "agent1",
   "status": "ready",
   "callback_url": f"http://127.0.0.1:{callback_port}/ingest"
  }).encode()
  
  _logger.info(f"[REGISTER] Sending to URL: {url}")
  _logger.info(f"[REGISTER] Body: {body}")
  
  req = urllib.request.Request(
   url,
   data=body,
   method="POST",
   headers={"Content-Type": "application/json", "Content-Length": str(len(body))}
  )
  
  with urllib.request.urlopen(req, timeout=5) as resp:
   result = json.loads(resp.read())
   _logger.info(f"[REGISTER] Response: {result}")
   return True
   
 except urllib.error.HTTPError as e:
  error_body = e.read().decode() if e.fp else str(e)
  _logger.error(f"[REGISTER] HTTP error: {e.code} - {e.reason}")
  _logger.error(f"[REGISTER] Response body: {error_body}")
  return False
 except Exception as e:
  _logger.error(f"[REGISTER] Exception: {type(e).__name__}: {e}")
  import traceback
  _logger.error(traceback.format_exc())
  return False

def on_window_evidence(evidence: WindowEvidence):
 global _graph
 
 ciso_tuples = []
 for opt in evidence.ciso_options:
    if hasattr(opt, 'category'):  # é um objeto CISOOption
      ciso_tuples.append((opt.category, opt.ciso_id, opt.probability, opt.risk_tier))
    else:  # já é um tuplo
      ciso_tuples.append(opt)
 
 confirmed = _graph.add_evidence(
  window_id=evidence.window_id,
  phases=evidence.phases,
  ciso_options=ciso_tuples,
  timestamp_ms=evidence.closed_at_ms,
  alert_ids=evidence.alert_ids,
 )
 
 _logger.info(f"Window evidence | window_id={evidence.window_id} | phases={evidence.phases} | "
    f"phase_score={evidence.phase_score} | alert_count={evidence.alert_count}")
 
 if confirmed:
  for label, score, tier, method in confirmed:
   _logger.info(f"*** CONFIRMED HYPOTHESIS: {label} (score={score:.3f}) by {method} ***")
   _console_logger.info(f"✓ CONFIRMED ({method}): {label}")
 
 _emit_graph_state()

def _emit_graph_state():
 ""
 global _graph
 
 if _graph is None:
  return
 
 state = _graph.get_graph_state()
 _emit_sse("graph_state_update", {
  "nodes": state.get("nodes", []),
  "edges": state.get("edges", []),
  "confirmed_hypotheses": state.get("confirmed_hypotheses", []),
  "kill_chain_progress": state.get("kill_chain_progress", {}),
  "total_evidence_windows": state.get("total_evidence_windows", 0),
  "pending_validations": state.get("pending_validations", []),
 })

def parse_timestamp(raw: str) -> int:
 ""
 if not raw:
  return 0
 
 try:
  dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
  return int(dt.timestamp() * 1000)
 except Exception:
  pass
 
 formats = [
  "%Y-%m-%d %H:%M:%S",
  "%Y-%m-%dT%H:%M:%SZ",
  "%Y/%m/%d %H:%M:%S",
 ]
 for fmt in formats:
  try:
   dt = datetime.strptime(raw, fmt)
   return int(dt.timestamp() * 1000)
  except ValueError:
   continue
 
 return 0

def parse_alert(block: List[str]) -> Optional[Dict]:
 ""
 alert = {}
 for line in block:
  if ":" not in line:
   continue
  idx = line.index(":")
  key = line[:idx].strip()
  value = line[idx + 1:].strip()
  if key:
   alert[key] = value
 
 if not alert:
  return None
 
 ts_raw = alert.get("SiemDetectionTime") or alert.get("AssignedAt") or alert.get("CreatedAt") or ""
 alert["_timestamp_ms"] = parse_timestamp(ts_raw)
 alert["@timestamp"] = datetime.fromtimestamp(
  alert["_timestamp_ms"] / 1000, tz=timezone.utc
 ).isoformat() if alert["_timestamp_ms"] else ""
 
 alert["Category"] = alert.get("Category", "").strip()
 alert["Type"] = alert.get("Type", "").strip()
 
 return alert

def load_alerts_from_file(filepath: Path) -> List[Dict]:
 ""
 if not filepath.exists():
  raise FileNotFoundError(f"Input file not found: {filepath}")
 
 alerts = []
 buffer = []
 
 with open(filepath, encoding="utf-8") as fh:
  for line in fh:
   line = line.strip()
   if not line or line.startswith("#"):
    continue
   if line == "----------":
    if buffer:
     alert = parse_alert(buffer)
     if alert and alert["_timestamp_ms"]:
      alerts.append(alert)
    buffer = []
   else:
    buffer.append(line)
 
 if buffer:
  alert = parse_alert(buffer)
  if alert and alert["_timestamp_ms"]:
   alerts.append(alert)
 
 return alerts

def save_dataset_bounds(alerts: List[Dict]) -> None:
 ""
 if not alerts:
  return
 
 first_ts = alerts[0]["_timestamp_ms"]
 last_ts = alerts[-1]["_timestamp_ms"]
 
 bounds = {
  "dataMinMs": first_ts,
  "dataMaxMs": last_ts,
  "total_alerts": len(alerts),
  "alerts": alerts,  
 }
 
 bounds_file = AGENT1_REPORTS_DIR / "dataset_bounds.json"
 bounds_file.write_text(json.dumps(bounds, indent=2), encoding="utf-8")
 _logger.info(f"Dataset bounds saved: {first_ts} -> {last_ts} ({len(alerts)} alerts)")

def process_alert_loop():
 ""
 global _window_manager, _graph, _current_alert_index, _all_alerts, _is_running
 
 _console_logger.info("Processamento de alertas iniciado. Aguardando alertas...")
 
 while _is_running:
  try:
   alert = _alert_queue.get(timeout=1)
   
   if alert is None:
    break
   
   alert_number = alert.get("Number", "unknown")
   
   if alert_number in _processed_alerts:
    _console_logger.warning(f"[PROCESS_LOOP] Ignoring duplicate: {alert_number}")
    continue
   
   _processed_alerts.add(alert_number)
   
   found_index = -1
   for idx, a in enumerate(_all_alerts):
    if a.get("Number") == alert_number:
     found_index = idx
     break
   
   if found_index >= 0:
    _current_alert_index = found_index
   else:
    _current_alert_index = len(_processed_alerts) - 1
   
   _console_logger.info(f"[{_current_alert_index + 1}/{len(_all_alerts)}] Processing: {alert_number}")
   _logger.info(f"Processing alert: {alert_number}")
   
   start_time = time.time()
   
   evidence = _window_manager.on_alert(
    alert,
    int(alert["_timestamp_ms"]),
    on_window_evidence
   )
   
   elapsed_ms = (time.time() - start_time) * 1000
   _logger.debug(f"Alert {alert_number} processed in {elapsed_ms:.2f}ms")
   
   _emit_sse("agent1_progress", {
    "current_index": _current_alert_index,
    "total_alerts": len(_all_alerts),
    "current_alert": alert_number,
    "active_windows": len(_window_manager.windows),
    "processing_time_ms": round(elapsed_ms, 2),
   })
   
   next_index = _current_alert_index + 1
   total = len(_all_alerts)
   is_last = next_index >= total

   if is_last:
    _emit_sse("next_alert_info", {
     "is_last": True,
     "current_alert_index": _current_alert_index,
     "current_alert_number": alert_number,
     "current_alert_category": alert.get("Category", ""),
     "current_alert_type": alert.get("Type", ""),
     "current_alert_timestamp_ms": alert.get("_timestamp_ms", 0),
     "total_alerts": total,
    })
    _emit_sse("done", {
     "source": "agent1",
     "total_alerts": total,
    })
    _console_logger.info(f"Todos os {total} alertas processados.")
   else:
    next_alert = _all_alerts[next_index]
    real_gap_ms = max(0, next_alert.get("_timestamp_ms", 0) - alert.get("_timestamp_ms", 0))
    _emit_sse("next_alert_info", {
     "is_last": False,
     "current_alert_index": _current_alert_index,
     "current_alert_number": alert_number,
     "current_alert_category": alert.get("Category", ""),
     "current_alert_type": alert.get("Type", ""),
     "current_alert_timestamp_ms": alert.get("_timestamp_ms", 0),
     "next_alert_index": next_index,
     "next_alert_number": next_alert.get("Number", ""),
     "next_alert_category": next_alert.get("Category", ""),
     "next_alert_type": next_alert.get("Type", ""),
     "next_alert_timestamp_ms": next_alert.get("_timestamp_ms", 0),
     "gap_ms": real_gap_ms,
     "real_gap_ms": real_gap_ms,
     "total_alerts": total,
    })

   _emit_graph_state()
   
   if _graph:
    auto_confirmed = _graph.auto_confirm_timeouts()
    if auto_confirmed:
     _console_logger.info(f"Auto-confirmed {len(auto_confirmed)} hypothesis(es) by timeout")
     _emit_graph_state()
   
  except queue.Empty:
   continue
  except Exception as e:
   _logger.error(f"Error in process loop: {e}", exc_info=True)
 
 _console_logger.info("Processamento de alertas terminado")

def run_streaming_mode():
 ""
 global _window_manager, _graph, _all_alerts, _current_alert_index, _is_running
 
 _console_logger.info("=" * 60)
 _console_logger.info("Agent 1 - Cognitive Security Engine")
 _console_logger.info("Modo: Streaming (escuta alertas via callback HTTP)")
 _console_logger.info(f"Janela CISO: {CISO_WINDOW_MINUTES} minutos")
 _console_logger.info(f"Máx. hipóteses: {PROBABILISTIC_MAX_HYPOTHESES}")
 _console_logger.info(f"Threshold confirmação: {CONFIRMATION_THRESHOLD}")
 _console_logger.info("=" * 60)
 
 _window_manager = WindowManager()
 _graph = get_global_graph()
 _is_running = True

 _start_sse_worker()
 
 _console_logger.info(f"Carregando alertas de: {INPUT_DATA_FILE}")
 _all_alerts = load_alerts_from_file(INPUT_DATA_FILE)
 _console_logger.info(f"Carregados {len(_all_alerts)} alertas")
 
 if not _all_alerts:
  _logger.warning("No alerts found. Exiting.")
  return
 
 save_dataset_bounds(_all_alerts)

 _console_logger.info("Iniciando servidor de callbacks na porta 8002...")
 callback_server = start_http_server_for_callbacks(8002)

 process_thread = threading.Thread(target=process_alert_loop, daemon=True, name="alert-processor")
 process_thread.start()
 _console_logger.info("Loop de processamento iniciado - aguardando alertas...")

 _console_logger.info("Registando com servidor SSE...")
 time.sleep(1)

 if register_with_sse_server(8002):
  _console_logger.info("✓ Registado com sucesso.")
 else:
  _console_logger.warning("⚠️ Não foi possível registar com servidor SSE")

 first_alert = _all_alerts[0]
 second_alert = _all_alerts[1] if len(_all_alerts) > 1 else None

 _emit_sse("dataset_bounds", {
  "dataMinMs": _all_alerts[0]["_timestamp_ms"],
  "dataMaxMs": _all_alerts[-1]["_timestamp_ms"],
  "total_alerts": len(_all_alerts),
  "speed_factor": STREAM_SPEED_FACTOR,
  "first_alert": {
   "index": 0,
   "number": first_alert.get("Number", ""),
   "category": first_alert.get("Category", ""),
   "type": first_alert.get("Type", ""),
   "timestamp_ms": first_alert["_timestamp_ms"],
  },
  "second_alert": {
   "index": 1,
   "number": second_alert.get("Number", "") if second_alert else "",
   "category": second_alert.get("Category", "") if second_alert else "",
   "type": second_alert.get("Type", "") if second_alert else "",
   "timestamp_ms": second_alert["_timestamp_ms"] if second_alert else 0,
  } if second_alert else None,
 })
 
 _console_logger.info("\n✅ Agente 1 pronto.")
 _console_logger.info(f"   {len(_all_alerts)} alertas carregados no dataset.")
 _console_logger.info("   O slice.ts controla o ritmo de entrega dos alertas.")
 _console_logger.info("   O Agente 1 processa APENAS quando recebe callback.")
 _console_logger.info("\n   Pressione Ctrl+C para parar.\n")
 
 try:
  while _is_running:
   time.sleep(1)
 except KeyboardInterrupt:
  _console_logger.info("\nAgente 1 parado pelo utilizador")
  _is_running = False
  _alert_queue.put(None)
  
 if _graph:
  top = _graph.get_top_hypotheses()
  _console_logger.info("\n📊 Top Hipóteses Globais (Hypothesis Graph):")
  for label, score, confirmed, tier in top[:5]:
   status = "✓" if confirmed else " "
   _console_logger.info(f"  [{status}] {label}: {score:.1%} ({tier})")
  
  pending = _graph.get_pending_validations()
  if pending:
   _console_logger.info(f"\n⏳ Validações pendentes: {len(pending)}")
 
 _console_logger.info("\nAté breve!")

def main():
 ""
 run_streaming_mode()

if __name__ == "__main__":
 main()