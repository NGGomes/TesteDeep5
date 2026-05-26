"""
Window Manager - Gerencia janelas adaptativas para análise de incidentes.

Dois modos (WINDOW_MODE em .env):
 fixed    — duração fixa CISO_WINDOW_MINUTES
 adaptive — duração calculada por fase do trigger + extensão automática
      quando chegam alertas de alta severidade dentro da janela.

O classificador probabilístico online é consultado em _update_ciso_options
para combinar o prior estático com experiência acumulada de confirmações.
"""
from __future__ import annotations

import os, uuid, threading, queue, json, urllib.request, time
from core.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
import sys
if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import (
  CISO_WINDOW_MINUTES, CISO_DECISION_TIMEOUT_SECONDS,
  MAX_PARALLEL_WINDOWS, PORT, DASHBOARD_HOST,
  PROBABILISTIC_MAX_HYPOTHESES, CONFIRMATION_THRESHOLD,
  WINDOW_MODE as _SHARED_WINDOW_MODE,
)
from agent1.mappings import (
  get_phase, generate_hypotheses, get_phases_from_sequence,
  calculate_phase_score, get_ciso_risk_tier,
)
from agent1.probabilistic_classifier import get_classifier

_logger = get_logger("AGENT1_.window_manager")

# ── Window mode ───────────────────────────────────────────────────────────────
# Use shared_config.WINDOW_MODE (lê o .env via python-dotenv antes do import)
# em vez de os.getenv() directamente, que apenas lê o ambiente do processo.
_WINDOW_MODE: str = _SHARED_WINDOW_MODE
_logger.info(f"[WindowManager] mode={_WINDOW_MODE}")

_PHASE_BASE_MINUTES: Dict[str, int] = {
  "RECON": 5, "INITIAL_ACCESS": 10, "EXECUTION": 15,
  "PERSISTENCE": 15, "LATERAL_MOVEMENT": 20, "EXFILTRATION": 25,
  "IMPACT": 30, "UNKNOWN": 10,
}
_ADAPTIVE_EXTENSION_MINUTES: int = 5
_ADAPTIVE_EXTENSION_WEIGHT_MIN: int = 5  # LATERAL_MOVEMENT and above

def _compute_window_minutes(trigger_phase: str) -> int:
  if _WINDOW_MODE == "adaptive":
    return _PHASE_BASE_MINUTES.get(trigger_phase, CISO_WINDOW_MINUTES)
  return CISO_WINDOW_MINUTES

# ── SSE queue ─────────────────────────────────────────────────────────────────
_sse_queue: queue.Queue = queue.Queue(maxsize=500)

def _sse_worker() -> None:
  import urllib.request as _ur
  while True:
    try:
      item = _sse_queue.get(timeout=5)
      if item is None:
        break
      etype, payload = item
      try:
        url = f"http://{DASHBOARD_HOST}:{PORT}/ingest"
        body = json.dumps([{"type": etype, "payload": payload}],
                 ensure_ascii=False, default=str).encode()
        req = _ur.Request(url, data=body,
                 headers={"Content-Type": "application/json"}, method="POST")
        with _ur.urlopen(req, timeout=2): pass
      except Exception: pass
    except queue.Empty: continue

threading.Thread(target=_sse_worker, daemon=True, name="wm-sse-worker").start()

def _emit_sse(event_type: str, payload: dict, blocking: bool = False) -> bool:
  if blocking:
    try:
      url = f"http://{DASHBOARD_HOST}:{PORT}/ingest"
      body = json.dumps([{"type": event_type, "payload": payload}],
               ensure_ascii=False, default=str).encode()
      req = urllib.request.Request(url, data=body,
                    headers={"Content-Type": "application/json"}, method="POST")
      with urllib.request.urlopen(req, timeout=2) as resp:
        return json.loads(resp.read()).get("ok", False)
    except Exception: return False
  try:
    _sse_queue.put_nowait((event_type, payload)); return True
  except queue.Full: return False

# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class WindowAlert:
  alert_id: str; timestamp_ms: int; timestamp_iso: str
  category: str; alert_type: str; phase: str
  phase_weight: float; is_noise: bool = False

@dataclass
class CISOOption:
  category: str; 
  ciso_id: int; 
  probability: float; 
  risk_tier: str

@dataclass
class WindowEvidence:
  window_id: str; 
  phases: List[str]; 
  phase_score: int
  ciso_options: List[CISOOption]; 
  created_at_ms: int
  closed_at_ms: int; 
  alert_count: int; 
  alert_ids: List[str] = None

# ── AdaptiveWindow ─────────────────────────────────────────────────────────────
class AdaptiveWindow:
  def __init__(self, trigger_alert: Dict, timestamp_ms: int):
    self.window_id          = str(uuid.uuid4())[:8]
    self.trigger_alert      = trigger_alert
    self.created_at_ms      = timestamp_ms
    self._real_created_ms   = int(time.time() * 1000)  # wall-clock, for reaper

    trig_phase, _           = get_phase(
      trigger_alert.get("Category", ""), trigger_alert.get("Type", ""))
    self.trigger_phase      = trig_phase
    self.window_mode        = _WINDOW_MODE
    self.window_minutes     = _compute_window_minutes(trig_phase)
    self.expires_at_ms      = timestamp_ms + self.window_minutes * 60_000
    self.decision_deadline_ms = timestamp_ms + CISO_DECISION_TIMEOUT_SECONDS * 1_000

    self.alerts: List[WindowAlert]               = []
    self.phases: List[str]                       = []
    self.ciso_options_history: List[List[CISOOption]] = []
    self.is_closed                               = False
    self.close_reason: Optional[str]             = None
    self.final_ciso_options: List[CISOOption]    = []
    self._lock                                   = threading.RLock()
    self._emitted_alert_ids: set                 = set()
    self.validation_requested                    = False
    self.validation_sent_at_ms: Optional[float]  = None
    self.validation_completed                    = False

    self._add_alert(trigger_alert, timestamp_ms)
    self._emit_created()

  # ── Adaptive extension ────────────────────────────────────────────────────
  def _try_extend(self, phase: str, weight: float) -> None:
    if _WINDOW_MODE != "adaptive" or self.is_closed:
      return
    if weight >= _ADAPTIVE_EXTENSION_WEIGHT_MIN:
      ext_ms   = _ADAPTIVE_EXTENSION_MINUTES * 60_000
      hard_cap = self.created_at_ms + 60 * 60_000  # max 60 min total
      new_exp  = min(self.expires_at_ms + ext_ms, hard_cap)
      if new_exp > self.expires_at_ms:
        self.expires_at_ms  = new_exp
        self.window_minutes = int((new_exp - self.created_at_ms) / 60_000)
        _logger.debug(
          f"[{self.window_id}] Extended +{_ADAPTIVE_EXTENSION_MINUTES}m"
          f" (phase={phase}, w={weight}) → {self.window_minutes}m total")

  # ── SSE ───────────────────────────────────────────────────────────────────
  def _emit_created(self):
    cur = self.ciso_options_history[-1] if self.ciso_options_history else []
    _emit_sse("window_created", {
    "window_id": self.window_id, "created_at_ms": self.created_at_ms,
    "expires_at_ms": self.expires_at_ms, "window_minutes": self.window_minutes,
    "window_mode": self.window_mode, "trigger_phase": self.trigger_phase,
    "phases": self.phases.copy(),
    "phase_score": calculate_phase_score(self.phases),
    "alert_count": len(self.alerts),
    "ciso_options": [
      {"category": o.category, "probability": o.probability, "risk_tier": o.risk_tier}
      for o in cur
    ],
    "trigger_alert": {
      "number": self.trigger_alert.get("Number", ""),
      "category": self.trigger_alert.get("Category", ""),
      "type": self.trigger_alert.get("Type", ""),
      "timestamp_ms": self.created_at_ms,  
      "severity":     self.trigger_alert.get("Severity", "medium").lower(),  
      "phase":        self.trigger_phase,   
    }
    }, blocking=True)
    
  def _emit_update(self):
    cur = self.ciso_options_history[-1] if self.ciso_options_history else []
    for a in self.alerts:
      if a.alert_id not in self._emitted_alert_ids:
        _emit_sse("alert", {
          "window_id": self.window_id, "number": a.alert_id,
          "timestamp_ms": a.timestamp_ms, "timestamp_iso": a.timestamp_iso,
          "category": a.category, "type": a.alert_type,
          "phase": a.phase, "severity": "medium",
          "title": f"{a.category} / {a.alert_type}", "source": "agente1",
          "kill_chain": a.phase,
          "phases_detected": [a.phase] if a.phase != "UNKNOWN" else [],
          "is_noise": a.is_noise,
        })
        self._emitted_alert_ids.add(a.alert_id)
    _emit_sse("window_updated", {
      "window_id": self.window_id, "alert_count": len(self.alerts),
      "phases": self.phases.copy(), "phase_score": calculate_phase_score(self.phases),
      "expires_at_ms": self.expires_at_ms, "window_minutes": self.window_minutes,
      "window_mode": self.window_mode,
      "ciso_options": [
        {"category": o.category, "probability": o.probability, "risk_tier": o.risk_tier}
        for o in cur
      ],
    })

  def _emit_closed(self):
    _emit_sse("window_closed", {
      "window_id": self.window_id, "reason": self.close_reason,
      "final_ciso_options": [
        {"category": o.category, "probability": o.probability, "risk_tier": o.risk_tier}
        for o in self.final_ciso_options
      ],
      "phases": self.phases.copy(), "phase_score": calculate_phase_score(self.phases),
      "alert_count": len(self.alerts), "window_minutes": self.window_minutes,
    })

  # ── Alert processing ──────────────────────────────────────────────────────
  def _add_alert(self, alert: Dict, timestamp_ms: int) -> None:
    cat        = alert.get("Category", "")
    atype      = alert.get("Type", "")
    resolution = alert.get("Resolution", "").lower()
    phase, weight = get_phase(cat, atype)
    is_noise   = (resolution == "falsepositive"
           or "spam" in cat.lower() or "noise" in cat.lower())

    self.alerts.append(WindowAlert(
      alert_id=alert.get("Number", ""), timestamp_ms=timestamp_ms,
      timestamp_iso=alert.get("@timestamp", ""), category=cat,
      alert_type=atype,
      phase=phase if not is_noise else "NOISE",
      phase_weight=weight if not is_noise else 0,
      is_noise=is_noise,
    ))
    if phase != "UNKNOWN" and not is_noise and phase not in self.phases:
      self.phases.append(phase)
    if not is_noise:
      self._try_extend(phase, weight)
    self._update_ciso_options()

  def _update_ciso_options(self) -> None:
        """Blend static prior with learned classifier probabilities."""
        unique_phases = get_phases_from_sequence(self.phases)
        prior = generate_hypotheses(unique_phases)  # [(cat, prob), ...]
        blended = get_classifier().predict(unique_phases, prior)  # [(cat, ciso_id, prob), ...]
        
        options = []
        for cat, ciso_id, prob in blended[:PROBABILISTIC_MAX_HYPOTHESES]:
            options.append(CISOOption(
                category=cat,
                ciso_id=ciso_id,
                probability=round(prob, 4),
                risk_tier=get_ciso_risk_tier(ciso_id)
            ))
        
        self.ciso_options_history.append(options)
        self._emit_update()
        self._check_convergence()
        
  def _check_convergence(self) -> None:
    if not self.ciso_options_history: return
    cur = self.ciso_options_history[-1]
    if not cur: return
    prob = cur[0].probability
    n    = len(self.alerts)
    # Normal convergence: strong evidence from multiple alerts
    normal       = prob >= CONFIRMATION_THRESHOLD and n >= 3
    # Exception: near-certain classification even with few alerts
    high_conf    = prob >= 0.97 and n >= 1
    if (normal or high_conf) and not self.is_closed:
      self.is_closed    = True
      self.close_reason = "convergence"
      self.final_ciso_options = cur
      self._emit_closed()

  def add_alert(self, alert: Dict, timestamp_ms: int) -> bool:
    with self._lock:
      if self.is_closed: return False
      if timestamp_ms <= self.expires_at_ms:
        self._add_alert(alert, timestamp_ms); return True
      return False

  def check_timeout(self, current_time_ms: int) -> bool:
    with self._lock:
      if self.is_closed: return False
      if current_time_ms >= self.expires_at_ms:
        self.is_closed = True; self.close_reason = "timeout"
        self.final_ciso_options = (
          self.ciso_options_history[-1] if self.ciso_options_history else [])
        self._emit_closed(); return True
      return False

  def request_operator_validation(self) -> bool:
    with self._lock:
      if self.validation_requested or self.validation_completed or not self.is_closed: return False
      if not self.final_ciso_options: return False
      if self.final_ciso_options[0].probability >= CONFIRMATION_THRESHOLD: return False
      self.validation_requested = True
      self.validation_sent_at_ms = time.time() * 1000
      _emit_sse("validation_requested", {
        "window_id": self.window_id,
        "hypotheses": [
          {"category": o.category, "probability": o.probability, "risk_tier": o.risk_tier}
          for o in self.final_ciso_options
        ],
        "phases": self.phases, "alert_count": len(self.alerts),
        "alert_ids": [a.alert_id for a in self.alerts],
        "timeout_seconds": CISO_DECISION_TIMEOUT_SECONDS,
      })
      return True

  def get_evidence(self) -> Optional[WindowEvidence]:
    with self._lock:
      if not self.is_closed or not self.final_ciso_options: 
        return None
      # Converter CISOOption para tuplo para o graph
      ciso_tuples = [
          (opt.category, opt.ciso_id, opt.probability, opt.risk_tier)
          for opt in self.final_ciso_options
      ]
      return WindowEvidence(
        window_id=self.window_id, 
        phases=self.phases.copy(),
        phase_score=calculate_phase_score(self.phases),
        ciso_options=ciso_tuples,
        created_at_ms=self.created_at_ms,
        closed_at_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        alert_count=len(self.alerts),
        alert_ids=[a.alert_id for a in self.alerts],
      )

  def get_state(self) -> dict:
    with self._lock:
      cur = self.ciso_options_history[-1] if self.ciso_options_history else []
      return {
        "window_id": self.window_id, "created_at_ms": self.created_at_ms,
        "expires_at_ms": self.expires_at_ms, "window_minutes": self.window_minutes,
        "window_mode": self.window_mode, "trigger_phase": self.trigger_phase,
        "alert_count": len(self.alerts), "phases": self.phases.copy(),
        "phase_score": calculate_phase_score(self.phases),
        "is_closed": self.is_closed, "close_reason": self.close_reason,
        "validation_requested": self.validation_requested,
        "current_ciso_options": [
          {"category": o.category, "probability": o.probability, "risk_tier": o.risk_tier}
          for o in cur
        ],
      }

# ── Singleton ────────────────────────────────────────────────────────────────
_global_window_manager: Optional["WindowManager"] = None

def get_window_manager() -> Optional["WindowManager"]:
  """Return the global WindowManager instance."""
  return _global_window_manager

def set_window_manager(wm: "WindowManager") -> None:
  """Register the global WindowManager instance."""
  global _global_window_manager
  _global_window_manager = wm

# ── WindowManager ─────────────────────────────────────────────────────────────
class WindowManager:
  def __init__(self):
    self.windows: Dict[str, AdaptiveWindow] = {}
    self._lock = threading.RLock()
    self._window_counter = 0
    self._closed_windows_evidence: List[WindowEvidence] = []
    # Auto-register as global singleton
    set_window_manager(self)
    self._start_reaper()

  def _start_reaper(self) -> None:
    import threading as _t
    def _reap():
      while True:
        time.sleep(10)
        now_real_ms = int(time.time() * 1000)
        with self._lock:
          to_close = []
          for wid, w in self.windows.items():
            if w.is_closed:
              continue
            real_created = getattr(w, '_real_created_ms', None)
            win_minutes  = getattr(w, 'window_minutes', 0)
            if not real_created or not win_minutes:
              continue  # ← skip se atributos não disponíveis ainda
            real_expiry = real_created + (win_minutes * 60_000)
            if now_real_ms >= real_expiry:
              to_close.append(wid)
          for wid in to_close:
            w = self.windows[wid]
            w.is_closed    = True
            w.close_reason = "timeout"
            w.final_ciso_options = (
              w.ciso_options_history[-1] if w.ciso_options_history else [])
            ev = w.get_evidence()
            if ev:
              self._closed_windows_evidence.append(ev)
            _logger.info(f"[Reaper] Window {wid} reaped ({win_minutes}m real timeout)")
            del self.windows[wid]
    _t.Thread(target=_reap, daemon=True, name="wm-reaper").start()
      
  def on_alert(self, alert: Dict, timestamp_ms: int,
             on_evidence_callback: Optional[Callable] = None) -> Optional[WindowEvidence]:
    evidence_list = []
    cat        = alert.get("Category", "").lower()
    resolution = alert.get("Resolution", "").lower()
    is_noise_alert = str(alert.get("IsNoiseAlert", "false")).strip().lower() == "true"
    is_noise = (resolution == "falsepositive"
                or "spam" in cat or "noise" in cat
                or is_noise_alert)
    
    # Emitir alertas noise para a timeline (a cinzento) mesmo descartando
    phase, _ = get_phase(alert.get("Category", ""), alert.get("Type", ""))
    _emit_sse("alert", {
            "window_id":     None,
            "number":        alert.get("Number", ""),
            "timestamp_ms":  timestamp_ms,
            "timestamp_iso": alert.get("@timestamp", ""),
            "category":      alert.get("Category", ""),
            "type":          alert.get("Type", ""),
            "phase":         phase,
            "severity":      alert.get("Severity", "low").lower(),
            "title":         alert.get("Title", ""),
            "source":        alert.get("Source", ""),
            "kill_chain":    phase,
            "phases_detected": [] if is_noise else ([phase] if phase != "UNKNOWN" else []),
            "is_noise":      is_noise,
    })
    if is_noise:
      return None
    with self._lock:
      to_remove = []

      # ── Step 1: try to add to existing open windows ──────────────────────
      added_to_existing = False
      for wid, window in list(self.windows.items()):
        if window.is_closed:
          to_remove.append(wid)
          continue
        accepted = window.add_alert(alert, timestamp_ms)
        if accepted:
          added_to_existing = True
        ev = window.get_evidence()
        if ev:
          evidence_list.append(ev)
          to_remove.append(wid)

      # ── Step 2: create new window ONLY if alert fits nowhere ─────────────
      if not is_noise and not added_to_existing:
        new_window = AdaptiveWindow(alert, timestamp_ms)
        self.windows[new_window.window_id] = new_window
        self._window_counter += 1

      # ── Step 3: remove closed windows, fire callbacks ────────────────────
      for wid in set(to_remove):
        if wid in self.windows:
          cw = self.windows[wid]
          ev = cw.get_evidence()
          if ev:
            self._closed_windows_evidence.append(ev)
            if on_evidence_callback: on_evidence_callback(ev)
          del self.windows[wid]

      # ── Step 4: check timeouts ────────────────────────────────────────────
      for wid, window in list(self.windows.items()):
        if window.check_timeout(timestamp_ms):
          ev = window.get_evidence()
          if ev:
            evidence_list.append(ev)
            if on_evidence_callback: on_evidence_callback(ev)
          if wid in self.windows: del self.windows[wid]

      # ── Step 5: reap oldest if over limit — WITH evidence callback ────────
      if len(self.windows) > MAX_PARALLEL_WINDOWS:
        oldest = sorted(self.windows.items(),
                        key=lambda x: x[1].created_at_ms)[:MAX_PARALLEL_WINDOWS // 2]
        for wid, window in oldest:
          window.is_closed    = True
          window.close_reason = "timeout"
          window.final_ciso_options = (
            window.ciso_options_history[-1] if window.ciso_options_history else [])
          ev = window.get_evidence()
          if ev:
            self._closed_windows_evidence.append(ev)
            if on_evidence_callback: on_evidence_callback(ev)
          del self.windows[wid]

    for ev in evidence_list:
      if on_evidence_callback: on_evidence_callback(ev)

    return evidence_list[0] if evidence_list else None  

  def request_validation_for_window(self, window_id: str) -> bool:
    with self._lock:
      if window_id not in self.windows: return False
      return self.windows[window_id].request_operator_validation()

  def get_all_windows_state(self) -> List[dict]:
    with self._lock:
      return [w.get_state() for w in self.windows.values()]

  def get_closed_windows_evidence(self) -> List[WindowEvidence]:
    with self._lock:
      return self._closed_windows_evidence.copy()

  def get_statistics(self) -> dict:
    with self._lock:
      return {
        "active_windows": len(self.windows),
        "total_windows_created": self._window_counter,
        "total_closed": len(self._closed_windows_evidence),
        "window_mode": _WINDOW_MODE,
        "classifier_stats": get_classifier().get_stats(),
        "avg_alerts_per_window": (
          sum(len(w.alerts) for w in self.windows.values())
          / max(len(self.windows), 1)
        ),
      }

  def reset(self) -> None:
    with self._lock:
      self.windows.clear()
      self._window_counter = 0
      self._closed_windows_evidence.clear()

  def close_window(self, window_id: str, reason: str = "operator") -> bool:
    """Force-close a window immediately — used after operator confirmation."""
    with self._lock:
      window = self.windows.get(window_id)
      if window is None:
        return False
      window.is_closed    = True
      window.close_reason = reason
      ev = window.get_evidence()
      if ev:
        self._closed_windows_evidence.append(ev)
      del self.windows[window_id]
      _logger.info(f"[WindowManager] Window {window_id} force-closed: {reason}")
      return True
