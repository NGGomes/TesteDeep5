"""
Hypothesis Graph - Memória global de hipóteses confirmadas.
"""

from __future__ import annotations

import json
import math
import threading
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
from core.logging import get_logger

_logger = get_logger("agent1.hypothesis_graph")

import sys
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import (
  HYPOTHESIS_DECAY_HOURS,
  CONFIRMATION_THRESHOLD,
  MAX_HYPOTHESES_PER_NODE,
  AGENT1_REPORTS_DIR,
  PORT,
  DASHBOARD_HOST,
)
from agent1.mappings import PHASE_PRIORITY
from agent1.probabilistic_classifier import get_classifier

# Canonical kill-chain order used for global edge inference
_PHASE_ORDER = ["RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE",
        "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"]
_PHASE_RANK = {p: i for i, p in enumerate(_PHASE_ORDER)}

def _emit_sse(event_type: str, payload: dict) -> bool:
  try:
    url = f"http://{DASHBOARD_HOST}:{PORT}/ingest"
    body = json.dumps([{"type": event_type, "payload": payload}], ensure_ascii=False, default=str).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=2) as resp:
      return json.loads(resp.read()).get("ok", False)
  except Exception:
    return False

@dataclass
class GraphNode:
  label: str
  cumulative_score: float = 0.0
  evidence_count: int = 0
  last_updated_ms: float = 0.0
  confirmed: bool = False
  confirmation_time_ms: float = 0.0
  risk_tier: str = "MEDIUM"
  confirmed_by: str = "auto"

@dataclass
class GraphEdge:
  source_phase: str
  target_phase: str
  weight: float = 1.0
  evidence_count: int = 0
  last_updated_ms: float = 0.0

@dataclass
class PendingValidation:
  hypothesis_label: str
  probability: float
  risk_tier: str
  phases: List[str]
  evidence_count: int
  created_at_ms: float
  expires_at_ms: float
  window_id: str
  alert_ids: List[str] = field(default_factory=list)
  ciso_options: List[Dict] = field(default_factory=list)

class HypothesisGraph:
  def __init__(self):
    self._nodes: Dict[str, GraphNode] = {}
    self._edges: Dict[Tuple[str, str], GraphEdge] = {}
    self._phase_sequence_cache: Dict[Tuple[str, ...], List[Tuple[str, float]]] = {}
    self._lock = threading.RLock()
    self._confirmed_hypotheses: Set[str] = set()
    self._last_confirmation_time: Dict[str, float] = {}
    self._window_evidence_log: List[Dict] = []

    self._pending_validations: Dict[str, PendingValidation] = {}
    self._validation_timeout_seconds: int = 60
    self._confirmed_by_operator: Set[str] = set()
    self._confirmed_by_timeout: Set[str] = set()

    # Global set of all phases ever seen across all windows.
    # Used to build kill-chain edges that span multiple windows.
    self._global_phases_seen: Set[str] = set()

    self._load_persistent_state()

  def _load_persistent_state(self) -> None:
    graph_file = AGENT1_REPORTS_DIR / "hypothesis_graph.json"
    if graph_file.exists():
      try:
        with open(graph_file, 'r', encoding='utf-8') as f:
          data = json.load(f)

        for label, node_data in data.get("nodes", {}).items():
          self._nodes[label] = GraphNode(
            label=label,
            cumulative_score=node_data.get("cumulative_score", 0.0),
            evidence_count=node_data.get("evidence_count", 0),
            last_updated_ms=node_data.get("last_updated_ms", 0.0),
            confirmed=node_data.get("confirmed", False),
            confirmation_time_ms=node_data.get("confirmation_time_ms", 0.0),
            risk_tier=node_data.get("risk_tier", "MEDIUM"),
            confirmed_by=node_data.get("confirmed_by", "auto"),
          )

        for edge_key, edge_data in data.get("edges", {}).items():
          parts = edge_key.split("→")
          if len(parts) == 2:
            self._edges[(parts[0], parts[1])] = GraphEdge(
              source_phase=parts[0],
              target_phase=parts[1],
              weight=edge_data.get("weight", 1.0),
              evidence_count=edge_data.get("evidence_count", 0),
              last_updated_ms=edge_data.get("last_updated_ms", 0.0),
            )

        self._confirmed_hypotheses = set(data.get("confirmed_hypotheses", []))
        self._last_confirmation_time = data.get("last_confirmation_time", {})
        self._window_evidence_log = data.get("window_evidence_log", [])
        self._global_phases_seen = set(data.get("global_phases_seen", []))

        pending_data = data.get("pending_validations", {})
        for window_id, pending in pending_data.items():
          self._pending_validations[window_id] = PendingValidation(
            hypothesis_label=pending.get("hypothesis_label", ""),
            probability=pending.get("probability", 0.0),
            risk_tier=pending.get("risk_tier", "MEDIUM"),
            phases=pending.get("phases", []),
            evidence_count=pending.get("evidence_count", 0),
            created_at_ms=pending.get("created_at_ms", 0),
            expires_at_ms=pending.get("expires_at_ms", 0),
            window_id=window_id,
            alert_ids=pending.get("alert_ids", []),
            ciso_options=pending.get("ciso_options", []),
          )

        _logger.info(f"[HypothesisGraph] Loaded {len(self._nodes)} nodes, {len(self._edges)} edges, "
              f"{len(self._pending_validations)} pending validations")
      except Exception as e:
        _logger.error(f"Failed to load state: {e}")

  def _save_persistent_state(self) -> None:
    graph_file = AGENT1_REPORTS_DIR / "hypothesis_graph.json"
    try:
      data = {
        "nodes": {
          label: {
            "cumulative_score": node.cumulative_score,
            "evidence_count": node.evidence_count,
            "last_updated_ms": node.last_updated_ms,
            "confirmed": node.confirmed,
            "confirmation_time_ms": node.confirmation_time_ms,
            "risk_tier": node.risk_tier,
            "confirmed_by": node.confirmed_by,
          }
          for label, node in self._nodes.items()
        },
        "edges": {
          f"{e.source_phase}→{e.target_phase}": {
            "weight": e.weight,
            "evidence_count": e.evidence_count,
            "last_updated_ms": e.last_updated_ms,
          }
          for e in self._edges.values()
        },
        "confirmed_hypotheses": list(self._confirmed_hypotheses),
        "last_confirmation_time": self._last_confirmation_time,
        "window_evidence_log": self._window_evidence_log[-100:],
        "global_phases_seen": list(self._global_phases_seen),
        "pending_validations": {
          wid: {
            "hypothesis_label": p.hypothesis_label,
            "probability": p.probability,
            "risk_tier": p.risk_tier,
            "phases": p.phases,
            "evidence_count": p.evidence_count,
            "created_at_ms": p.created_at_ms,
            "expires_at_ms": p.expires_at_ms,
            "window_id": p.window_id,
            "alert_ids": p.alert_ids,
            "ciso_options": p.ciso_options,
          }
          for wid, p in self._pending_validations.items()
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
      }
      with open(graph_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    except Exception as e:
      _logger.error(f"Failed to save state: {e}")

  def _apply_decay(self, current_time_ms: float) -> None:
    with self._lock:
      for node in self._nodes.values():
        if node.last_updated_ms > 0:
          age_ms = current_time_ms - node.last_updated_ms
          if age_ms > 0:
            decay = math.exp(-age_ms / (HYPOTHESIS_DECAY_HOURS * 3600 * 1000))
            node.cumulative_score = node.cumulative_score * decay

      for edge in self._edges.values():
        if edge.last_updated_ms > 0:
          age_ms = current_time_ms - edge.last_updated_ms
          if age_ms > 0:
            decay = math.exp(-age_ms / (HYPOTHESIS_DECAY_HOURS * 3600 * 1000))
            edge.weight = edge.weight * decay

  def _update_global_kill_chain_edges(self, new_phases: List[str], timestamp_ms: float) -> None:
    """Build kill-chain edges from the globally accumulated phase set.

    Each time a window closes with new phases, we add those phases to the
    global set and then create/reinforce edges for every consecutive pair
    in canonical kill-chain order that are both present globally.  This
    ensures the kill-chain progress reflects the full campaign even when
    individual windows only capture a subset of phases.
    """
    for p in new_phases:
      if p in _PHASE_RANK:
        self._global_phases_seen.add(p)

    # Sort globally-seen phases by canonical order
    ordered = sorted(
      [p for p in self._global_phases_seen if p in _PHASE_RANK],
      key=lambda p: _PHASE_RANK[p]
    )

    # Create/reinforce edges between every consecutive pair
    for i in range(len(ordered) - 1):
      src = ordered[i]
      tgt = ordered[i + 1]
      # Only create edge if they are adjacent in the canonical chain
      if _PHASE_RANK[tgt] == _PHASE_RANK[src] + 1:
        edge_key = (src, tgt)
        if edge_key not in self._edges:
          self._edges[edge_key] = GraphEdge(
            source_phase=src,
            target_phase=tgt,
            weight=1.0,
          )
        edge = self._edges[edge_key]
        edge.weight = min(1.0, edge.weight + 0.1)
        edge.evidence_count += 1
        edge.last_updated_ms = timestamp_ms

  
  def add_evidence(self,
                 window_id: str,
                 phases: List[str],
                 ciso_options: List[Tuple],
                 timestamp_ms: float,
                 alert_ids: Optional[List[str]] = None) -> List[Tuple[str, float, str, str]]:
    confirmed = []

    with self._lock:
        self._apply_decay(timestamp_ms)

        # Helper para normalizar qualquer tuplo para (cat, prob, tier)
        def normalize_opt(opt):
            if len(opt) == 4:
                cat, ciso_id, prob, tier = opt
                return cat, prob, tier
            else:  # len(opt) == 3
                return opt[0], opt[1], opt[2]
        
        # Normalizar todas as opções para o formato (cat, prob, tier)
        normalized_options = [normalize_opt(opt) for opt in ciso_options]
        
        # Construir log com formato seguro
        self._window_evidence_log.append({
            "window_id": window_id,
            "phases": phases,
            "alert_ids": alert_ids or [],
            "ciso_options": [
                {"category": cat, "probability": prob, "risk_tier": tier}
                for cat, prob, tier in normalized_options
            ],
            "timestamp_ms": timestamp_ms,
            "window_start_ms": timestamp_ms,
            "window_end_ms": timestamp_ms,
        })
        
        # Processar cada opção
        for cat, prob, tier in normalized_options[:MAX_HYPOTHESES_PER_NODE]:
            if cat not in self._nodes:
                self._nodes[cat] = GraphNode(
                    label=cat,
                    risk_tier=tier,
                )

            node = self._nodes[cat]

            old_prob = node.cumulative_score
            if old_prob > 0:
                new_prob = 1.0 - (1.0 - old_prob) * (1.0 - prob)
            else:
                new_prob = prob

            node.cumulative_score = new_prob
            node.evidence_count += 1
            node.last_updated_ms = timestamp_ms
            node.risk_tier = tier

            if new_prob >= CONFIRMATION_THRESHOLD and not node.confirmed:
                node.confirmed = True
                node.confirmation_time_ms = timestamp_ms
                node.confirmed_by = "auto"
                self._confirmed_hypotheses.add(cat)
                self._last_confirmation_time[cat] = timestamp_ms
                confirmed.append((cat, new_prob, tier, "auto"))

                _logger.info(f"*** AUTO-CONFIRMED: {cat} (score={new_prob:.3f}, evidence={node.evidence_count}) ***")

                _emit_sse("hypothesis_confirmed", {
                    "label": cat,
                    "score": new_prob,
                    "risk_tier": tier,
                    "method": "auto",
                    "evidence_count": node.evidence_count,
                    "confirmation_time_ms": timestamp_ms,
                })

        # Pending validations (usar opções normalizadas)
        if normalized_options:
            top_cat, top_prob, top_tier = normalized_options[0]
            top_node = self._nodes.get(top_cat)

            if top_node and not top_node.confirmed and top_prob < CONFIRMATION_THRESHOLD:
                if window_id not in self._pending_validations:
                    pending = PendingValidation(
                        hypothesis_label=top_cat,
                        probability=top_prob,
                        risk_tier=top_tier,
                        phases=phases.copy(),
                        evidence_count=top_node.evidence_count,
                        created_at_ms=timestamp_ms,
                        expires_at_ms=timestamp_ms + (self._validation_timeout_seconds * 1000),
                        window_id=window_id,
                        alert_ids=alert_ids or [],
                        ciso_options=[
                            {"category": cat, "probability": prob, "risk_tier": tier}
                            for cat, prob, tier in normalized_options[:3]
                        ],
                    )
                    self._pending_validations[window_id] = pending

                    _logger.info(f"*** VALIDATION PENDING: {top_cat} (score={top_prob:.3f}) - awaiting operator ***")

                    _emit_sse("validation_pending", {
                        "window_id": window_id,
                        "hypothesis": top_cat,
                        "probability": top_prob,
                        "risk_tier": top_tier,
                        "phases": phases,
                        "ciso_options": [
                            {"category": cat, "probability": prob, "risk_tier": tier}
                            for cat, prob, tier in normalized_options[:3]
                        ],
                        "timeout_seconds": self._validation_timeout_seconds,
                        "alert_count": len(alert_ids) if alert_ids else 0,
                    })

        # Update kill-chain edges
        for i in range(len(phases) - 1):
            src = phases[i]
            tgt = phases[i + 1]
            edge_key = (src, tgt)
            if edge_key not in self._edges:
                self._edges[edge_key] = GraphEdge(
                    source_phase=src,
                    target_phase=tgt,
                    weight=1.0,
                )
            edge = self._edges[edge_key]
            edge.weight = min(1.0, edge.weight + 0.1)
            edge.evidence_count += 1
            edge.last_updated_ms = timestamp_ms

        # Global kill-chain edge inference across all windows
        self._update_global_kill_chain_edges(phases, timestamp_ms)

        self._save_persistent_state()

    return confirmed

  def confirm_by_operator(self, window_id: str, hypothesis_label: str) -> bool:
    with self._lock:
      # Get confirmation data — from pending_validations if available,
      # otherwise reconstruct from graph state (high-confidence windows
      # may not have a pending validation entry)
      pending = self._pending_validations.get(window_id)

      if pending is not None:
        # Allow confirmation of any of the 3 options, not just the top
        probability = next(
          (o["probability"] for o in pending.ciso_options
          if o["category"] == hypothesis_label),
          pending.probability
        )
        risk_tier = next(
          (o["risk_tier"] for o in pending.ciso_options
          if o["category"] == hypothesis_label),
          pending.risk_tier
        )
        phases       = pending.phases
        evidence_count = pending.evidence_count
        ciso_options = pending.ciso_options
      else:
        # Window not in pending — look up node directly (high-confidence path)
        node_state = next(
          (n for n in self.get_graph_state().get("nodes", [])
          if n["label"] == hypothesis_label),
          None
        )
        if node_state is None:
          _logger.warning(f"confirm_by_operator: {hypothesis_label} not found in graph for window {window_id}")
          # Still allow — create minimal node
          probability    = 0.85
          risk_tier      = "HIGH"
          phases         = []
          evidence_count = 0
          ciso_options   = []
        else:
          probability    = node_state.get("cumulative_score", 0.85)
          risk_tier      = node_state.get("risk_tier", "HIGH")
          phases         = []
          evidence_count = node_state.get("evidence_count", 0)
          ciso_options   = []

      if hypothesis_label not in self._nodes:
        self._nodes[hypothesis_label] = GraphNode(
          label=hypothesis_label,
          risk_tier=risk_tier,
        )

      node = self._nodes[hypothesis_label]
      node.confirmed             = True
      node.confirmation_time_ms  = datetime.now(timezone.utc).timestamp() * 1000
      node.cumulative_score      = max(node.cumulative_score, probability)
      node.confirmed_by          = "operator"
      node.evidence_count        = max(node.evidence_count, evidence_count)

      self._confirmed_hypotheses.add(hypothesis_label)
      self._confirmed_by_operator.add(hypothesis_label)
      self._last_confirmation_time[hypothesis_label] = node.confirmation_time_ms

      # Remove from pending if present
      if window_id in self._pending_validations:
        del self._pending_validations[window_id]

      _logger.info(f"*** OPERATOR-CONFIRMED: {hypothesis_label} (score={node.cumulative_score:.3f}) ***")

      # Classifier feedback
      try:
        all_options = [(o["category"], o["probability"]) for o in ciso_options]
        if all_options:
          get_classifier().record_confirmation(
            phases=phases,
            confirmed_label=hypothesis_label,
            all_options=all_options,
          )
          _logger.info(f"[HypothesisGraph] Classifier updated: confirmed={hypothesis_label!r}")
      except Exception as e:
        _logger.warning(f"[HypothesisGraph] Classifier update failed: {e}")

      _emit_sse("hypothesis_confirmed", {
        "label":             hypothesis_label,
        "score":             node.cumulative_score,
        "risk_tier":         risk_tier,
        "method":            "operator",
        "window_id":         window_id,
        "evidence_count":    node.evidence_count,
        "classifier_updated": True,
      })

      self._save_persistent_state()
      return True

  def auto_confirm_timeouts(self) -> List[Tuple[str, float, str]]:
    confirmed = []
    now_ms = datetime.now(timezone.utc).timestamp() * 1000

    with self._lock:
      expired = [
        (wid, pending)
        for wid, pending in self._pending_validations.items()
        if now_ms >= pending.expires_at_ms
      ]

      for window_id, pending in expired:
        # Skip windows already confirmed by operator — never downgrade to timeout
        if pending.hypothesis_label in self._confirmed_by_operator:
          _logger.debug(f"[auto_confirm] Skipping {window_id} — already operator-confirmed")
          del self._pending_validations[window_id]
          continue

        if pending.hypothesis_label not in self._nodes:
          self._nodes[pending.hypothesis_label] = GraphNode(
            label=pending.hypothesis_label,
            risk_tier=pending.risk_tier,
          )

        node = self._nodes[pending.hypothesis_label]

        if not node.confirmed:
          node.confirmed = True
          node.confirmation_time_ms = now_ms
          node.cumulative_score = max(node.cumulative_score, pending.probability)
          node.confirmed_by = "timeout"
          node.evidence_count = max(node.evidence_count, pending.evidence_count)

          self._confirmed_hypotheses.add(pending.hypothesis_label)
          self._confirmed_by_timeout.add(pending.hypothesis_label)
          self._last_confirmation_time[pending.hypothesis_label] = now_ms

          confirmed.append((pending.hypothesis_label, node.cumulative_score, pending.risk_tier))

          _logger.info(f"*** TIMEOUT-CONFIRMED: {pending.hypothesis_label} (score={node.cumulative_score:.3f}) ***")

          _emit_sse("hypothesis_confirmed", {
            "label": pending.hypothesis_label,
            "score": node.cumulative_score,
            "risk_tier": pending.risk_tier,
            "method": "timeout",
            "window_id": window_id,
            "evidence_count": node.evidence_count,
          })

        del self._pending_validations[window_id]

      if confirmed:
        self._save_persistent_state()

    return confirmed

  def get_pending_validations(self) -> List[Dict]:
    with self._lock:
      result = []
      now_ms = datetime.now(timezone.utc).timestamp() * 1000

      for window_id, pending in self._pending_validations.items():
        remaining_ms = max(0, pending.expires_at_ms - now_ms)

        result.append({
          "window_id": window_id,
          "hypothesis": pending.hypothesis_label,
          "probability": pending.probability,
          "risk_tier": pending.risk_tier,
          "phases": pending.phases,
          "ciso_options": pending.ciso_options,
          "evidence_count": pending.evidence_count,
          "timeout_seconds": int(remaining_ms / 1000),
          "expired": remaining_ms <= 0,
          "created_at_ms": pending.created_at_ms,
          "expires_at_ms": pending.expires_at_ms,
        })

      return result

  def get_top_hypotheses(self, limit: int = MAX_HYPOTHESES_PER_NODE) -> List[Tuple[str, float, bool, str]]:
    with self._lock:
      sorted_nodes = sorted(
        [(label, node.cumulative_score, node.confirmed, node.risk_tier)
        for label, node in self._nodes.items()],
        key=lambda x: -x[1]
      )
      return sorted_nodes[:limit]

  def get_confirmed_hypotheses(self, since_timestamp_ms: float = 0) -> List[Tuple[str, float, float, str, str]]:
    with self._lock:
      result = []
      for label in self._confirmed_hypotheses:
        node = self._nodes.get(label)
        if node and node.confirmation_time_ms >= since_timestamp_ms:
          result.append((label, node.cumulative_score, node.confirmation_time_ms, node.risk_tier, node.confirmed_by))
      return sorted(result, key=lambda x: -x[1])

  def get_alert_ids_for_confirmations(
    self,
    confirmed_labels: Optional[List[str]] = None,
  ) -> List[str]:
    """Return all alert IDs seen across evidence windows that contributed to
    the given confirmed hypotheses.  If `confirmed_labels` is None, return
    alert IDs from ALL evidence windows.

    Used by graph_reporter to load the raw alerts for IOC/asset extraction.
    """
    with self._lock:
      alert_ids: List[str] = []
      seen: set = set()
      for entry in self._window_evidence_log:
        # Filter by label if requested
        if confirmed_labels is not None:
          entry_labels = {
            opt["category"]
            for opt in entry.get("ciso_options", [])
          }
          if not entry_labels.intersection(confirmed_labels):
            continue
        for aid in entry.get("alert_ids", []):
          if aid and aid not in seen:
            seen.add(aid)
            alert_ids.append(aid)
      return alert_ids

  def get_window_evidence_summary(self) -> List[Dict]:
    """Return a compact summary of all evidence windows."""
    with self._lock:
      summaries = []
      for e in self._window_evidence_log:
        ts    = e.get("timestamp_ms", 0)
        start = e.get("window_start_ms", ts)
        end   = e.get("window_end_ms", ts)
        summaries.append({
          "window_id":      e["window_id"],
          "phases":         e.get("phases", []),
          "alert_ids":      e.get("alert_ids", []),
          "alert_count":    len(e.get("alert_ids", [])),
          "timestamp_ms":   ts,
          "window_start_ms": start,
          "window_end_ms":   end,
          "phase_score":    len(e.get("phases", [])),
          "top_category":   (
            e["ciso_options"][0]["category"]
            if e.get("ciso_options") else ""
          ),
        })
      return summaries

  def get_kill_chain_progress(self) -> Dict[str, float]:
    """Return kill-chain progress based on global edge evidence.

    RECON is always 1.0 (start of chain). Each subsequent phase gets the
    weight of the edge from its predecessor — edges are created both from
    individual window phase sequences AND from the global phases-seen set,
    so the full campaign chain is always represented.
    """
    progress = {}
    for i, phase in enumerate(_PHASE_ORDER):
      if i == 0:
        progress[phase] = 1.0
      else:
        prev_phase = _PHASE_ORDER[i - 1]
        edge_key = (prev_phase, phase)
        if edge_key in self._edges:
          progress[phase] = min(1.0, self._edges[edge_key].weight)
        elif phase in self._global_phases_seen:
          # Phase was seen globally but edge not yet created — show it
          progress[phase] = 0.5
        else:
          progress[phase] = 0.0

    return progress

  def get_graph_state(self) -> dict:
    with self._lock:
      try:
        classifier_stats = get_classifier().get_stats()
      except Exception:
        classifier_stats = {}
      return {
        "nodes": [
          {
            "label": node.label,
            "cumulative_score": node.cumulative_score,
            "evidence_count": node.evidence_count,
            "confirmed": node.confirmed,
            "confirmation_time_ms": node.confirmation_time_ms,
            "risk_tier": node.risk_tier,
            "confirmed_by": node.confirmed_by,
          }
          for node in self._nodes.values()
        ],
        "edges": [
          {
            "source": e.source_phase,
            "target": e.target_phase,
            "weight": e.weight,
            "evidence_count": e.evidence_count,
          }
          for e in self._edges.values()
        ],
        "confirmed_hypotheses": list(self._confirmed_hypotheses),
        "kill_chain_progress": self.get_kill_chain_progress(),
        "total_evidence_windows": len(self._window_evidence_log),
        "pending_validations": self.get_pending_validations(),
        "classifier": classifier_stats,
      }

  def reset(self) -> None:
    with self._lock:
      self._nodes.clear()
      self._edges.clear()
      self._phase_sequence_cache.clear()
      self._confirmed_hypotheses.clear()
      self._last_confirmation_time.clear()
      self._window_evidence_log.clear()
      self._pending_validations.clear()
      self._confirmed_by_operator.clear()
      self._confirmed_by_timeout.clear()
      self._global_phases_seen.clear()
      self._save_persistent_state()
      _logger.info("HypothesisGraph reset")

_global_graph: Optional[HypothesisGraph] = None
_graph_lock = threading.Lock()

def get_global_graph() -> HypothesisGraph:
  global _global_graph
  with _graph_lock:
    if _global_graph is None:
      _global_graph = HypothesisGraph()
    return _global_graph

def reset_global_graph() -> None:
  global _global_graph
  with _graph_lock:
    if _global_graph is not None:
      _global_graph.reset()
    _global_graph = HypothesisGraph()
