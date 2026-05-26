"""
Agent 2 - Graph Reporter: Generates reports when hypotheses are confirmed.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import sys

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import (
    AGENT2_REPORTS_DIR,
    CONFIRMATION_THRESHOLD,
    PORT,
    DASHBOARD_HOST,
    AGENT2_POLL_SECONDS,
    INPUT_DATA_FILE,
    AGENT1_REPORTS_DIR,
    AGENT2_TIMEOUT_SECONDS,
)
from core.logging import get_logger

logger = get_logger("agent2.graph_reporter")

# Optional enrichment modules — non-fatal if missing
try:
    from agent2.llm_engine import (
        IncidentAnalyzer,
        LLMEnhancer,
        LLM_AVAILABLE,
        LLM_PROVIDER,
    )

    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False
    LLM_AVAILABLE = False
    LLM_PROVIDER = "none"

try:
    from agent2.latex_generator import CISOReportGenerator, SOCReportGenerator

    _HAS_LATEX = True
    logger.info("[GraphReporter] latex_generator loaded OK")
except ImportError as _e:
    _HAS_LATEX = False
    logger.warning(
        f"[GraphReporter] latex_generator not available: {_e} — .tex files will not be generated"
    )

try:
    from agent2.analyzers import DataExtractor

    _HAS_ANALYZERS = True
    logger.info("[GraphReporter] analyzers loaded OK")
except ImportError as _e:
    _HAS_ANALYZERS = False
    logger.warning(
        f"[GraphReporter] analyzers not available: {_e} — IOC/asset extraction disabled"
    )

# ============================================================================
# CONFIDENCE TABLE - importado da versão antiga
# ============================================================================

_CONFIDENCE_TABLE: List[Tuple[int, int, str]] = [
    (30, 6, "HIGH"),  # score >= 30 AND >= 6 kill chain phases
    (20, 5, "HIGH"),  # score >= 20 AND >= 5 phases
    (15, 5, "MEDIUM"),  # score >= 15 AND >= 5 phases
    (15, 3, "MEDIUM"),  # score >= 15 AND >= 3 phases
    (10, 4, "MEDIUM"),  # score >= 10 AND >= 4 phases
    (10, 2, "MEDIUM"),  # score >= 10 AND >= 2 phases
    (6, 3, "MEDIUM"),  # score >= 6 AND >= 3 phases
    (6, 1, "LOW"),  # score >= 6 AND >= 1 phase
    (3, 1, "LOW"),  # score >= 3 AND >= 1 phase
    (0, 0, "LOW"),  # fallback
]


def compute_confidence(score: float, n_kill_chain_phases: int) -> str:
    """Calcula o nível de confiança baseado no score e número de fases."""
    for min_score, min_phases, level in _CONFIDENCE_TABLE:
        if score >= min_score and n_kill_chain_phases >= min_phases:
            return level
    return "LOW"


# ============================================================================
# PHASE RESOLUTION - importado da versão antiga
# ============================================================================

_CISO_CATEGORY_TO_PHASE_OVERRIDE: Dict[str, str] = {
    "supply chain": "RECON",
    "third-party": "RECON",
    "third party": "RECON",
    "vulnerability": "INITIAL_ACCESS",
    "reconnaissance": "RECON",
    "credential": "INITIAL_ACCESS",
    "apt": "LATERAL_MOVEMENT",
    "advanced persistent": "LATERAL_MOVEMENT",
    "ransomware": "IMPACT",
    "destructive": "IMPACT",
    "wipeware": "IMPACT",
    "exfiltration": "EXFILTRATION",
    "data exfiltration": "EXFILTRATION",
    "persistence": "PERSISTENCE",
    "malware": "EXECUTION",
    "botnet": "EXECUTION",
}

_PHASE_PRIORITY: Dict[str, int] = {
    "RECON": 0,
    "INITIAL_ACCESS": 1,
    "EXECUTION": 2,
    "PERSISTENCE": 3,
    "LATERAL_MOVEMENT": 4,
    "EXFILTRATION": 5,
    "IMPACT": 6,
}


def resolve_primary_phase(
    primary_ciso_category: str,
    kill_chain_phases_detected: List[str],
) -> str:
    """Resolve a fase primária baseada na categoria CISO e fases detectadas."""
    if not kill_chain_phases_detected:
        cat_lower = primary_ciso_category.lower()
        for fragment, phase in _CISO_CATEGORY_TO_PHASE_OVERRIDE.items():
            if fragment in cat_lower:
                return phase
        return "UNKNOWN"

    sorted_phases = sorted(
        kill_chain_phases_detected,
        key=lambda p: _PHASE_PRIORITY.get(p, 99),
    )
    return sorted_phases[0]


class AlertLoader:
    """Loads the full alert dataset once and provides O(1) lookup by alert Number."""

    _cache: Optional[Dict[str, Dict]] = None  # Number → alert dict
    _cache_lock = threading.Lock()

    @classmethod
    def _build_cache(cls) -> Dict[str, Dict]:
        """Parse projD.txt (or dataset_bounds.json) into a Number-keyed dict."""
        alerts: Dict[str, Dict] = {}

        # Prefer the pre-parsed dataset_bounds.json (already loaded by Agent 1)
        bounds_file = AGENT1_REPORTS_DIR / "dataset_bounds.json"
        if bounds_file.exists():
            try:
                bounds = json.loads(bounds_file.read_text(encoding="utf-8"))
                for a in bounds.get("alerts", []):
                    num = a.get("Number") or a.get("number")
                    if num:
                        alerts[str(num)] = a
                if alerts:
                    logger.info(
                        f"[AlertLoader] Loaded {len(alerts)} alerts from dataset_bounds.json"
                    )
                    return alerts
            except Exception as e:
                logger.warning(f"[AlertLoader] dataset_bounds.json parse error: {e}")

        # Fallback: parse projD.txt directly
        if INPUT_DATA_FILE.exists():
            try:
                current: Dict[str, str] = {}
                for line in INPUT_DATA_FILE.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line == "----------":
                        if current and current.get("Number"):
                            alerts[current["Number"]] = dict(current)
                        current = {}
                    elif ":" in line:
                        k, _, v = line.partition(":")
                        current[k.strip()] = v.strip()
                if current and current.get("Number"):
                    alerts[current["Number"]] = dict(current)
                logger.info(
                    f"[AlertLoader] Loaded {len(alerts)} alerts from {INPUT_DATA_FILE.name}"
                )
            except Exception as e:
                logger.warning(f"[AlertLoader] projD.txt parse error: {e}")

        return alerts

    @classmethod
    def get_alerts_by_ids(cls, alert_ids: List[str]) -> List[Dict]:
        """Return full alert dicts for the given alert IDs (Numbers)."""
        with cls._cache_lock:
            if cls._cache is None:
                cls._cache = cls._build_cache()
        found = []
        for aid in alert_ids:
            a = cls._cache.get(str(aid))
            if a:
                found.append(a)
        return found

    @classmethod
    def invalidate(cls) -> None:
        with cls._cache_lock:
            cls._cache = None


def _emit_sse(event_type: str, payload: dict) -> bool:
    try:
        url = f"http://{DASHBOARD_HOST}:{PORT}/ingest"
        body = json.dumps(
            [{"type": event_type, "payload": payload}], ensure_ascii=False, default=str
        ).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception:
        return False


def _fmt_label(name: str) -> str:
    """Format a CISO category name as 'SHORTCODE  Full Name' for display."""
    try:
        from agent1.mappings import get_ciso_label

        return get_ciso_label(name)
    except Exception:
        return name


def _soc_recs_from_phases(phases: list) -> list:
    """Generate tactical SOC recommendations based on detected kill-chain phases."""
    recs = []
    phases_upper = [p.upper() for p in phases]
    if "RECON" in phases_upper:
        recs.append(
            "Review firewall/proxy logs for scanning activity; block suspicious IP ranges at perimeter."
        )
    if "INITIAL_ACCESS" in phases_upper:
        recs.append(
            "Audit authentication logs (Event IDs 4624/4625) for unusual logons; check phishing indicators."
        )
    if "EXECUTION" in phases_upper or "PERSISTENCE" in phases_upper:
        recs.append(
            "Scan all endpoints for malicious processes, scheduled tasks, and registry persistence keys."
        )
    if "LATERAL_MOVEMENT" in phases_upper:
        recs.append(
            "Isolate affected segments; audit AD for pass-the-hash/pass-the-ticket indicators (Event 4769)."
        )
    if "EXFILTRATION" in phases_upper:
        recs.append(
            "Block identified C2/exfil destinations at proxy; preserve NetFlow logs for forensic scope."
        )
    if "IMPACT" in phases_upper:
        recs.append(
            "Assess data integrity across affected systems; activate backup validation and restore procedures."
        )
    if not recs:
        recs.append(
            "Increase monitoring frequency on affected assets; review recent authentication events."
        )
    return recs


class GraphReporter:
    # Path for persistent queue — survives restarts
    _QUEUE_FILE = Path(AGENT2_REPORTS_DIR) / ".pending_queue.json"

    def __init__(self, poll_interval: int = 2):
        self._last_processed_confirmation_ms: float = 0
        self._generated_reports: List[Dict] = []
        self._lock = threading.RLock()
        self._running = False
        self._poll_interval = poll_interval
        self._graph = None

        # Persistent dedup set — labels successfully reported this process lifetime
        self._processed_confirmations: set = set()

        # Guaranteed delivery queue: label → entry
        # Added on confirm, removed only after successful _emit_report()
        # Persisted to disk so restarts don't lose queued reports
        self._pending_queue: dict = self._load_queue()
        self._queue_lock = threading.Lock()

        logger.info("=" * 60)
        logger.info("Agent 2 - Graph Reporter (Trigger-based)")
        logger.info(f"Confirmation threshold: {CONFIRMATION_THRESHOLD}")
        logger.info("Will generate reports when hypotheses are confirmed")
        logger.info("=" * 60)

    def _get_graph(self):
        if self._graph is None:
            try:
                from agent1.hypothesis_graph import get_global_graph

                self._graph = get_global_graph()
                logger.info("Connected to Hypothesis Graph")
            except ImportError as e:
                logger.error(f"Failed to import HypothesisGraph: {e}")
                return None
        return self._graph

    def _get_new_confirmations(self) -> List[Tuple[str, float, float, str, str]]:
        graph = self._get_graph()
        if graph is None:
            return []

        try:
            confirmations = graph.get_confirmed_hypotheses(
                since_timestamp_ms=self._last_processed_confirmation_ms
            )
            return confirmations
        except Exception as e:
            logger.error(f"Failed to get confirmations: {e}")
            return []

    def _get_graph_context(self) -> Dict[str, Any]:
        """Lê os alertas brutos do Agente 1 e normaliza os dados para o LaTeX e Dashboard."""
        alerts_list = []
        raw_iocs = set()
        raw_assets = set()

        try:
            graph_file = AGENT1_REPORTS_DIR / "hypothesis_graph.json"
            if graph_file.exists():
                with open(graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # No hypothesis_graph.json do Agente 1, os alertas costumam estar em 'all_alerts' ou 'alerts'
                    all_alerts = data.get("all_alerts", data.get("alerts", {}))

                    # Tenta localizar as confirmações ativas para capturar os IDs dos alertas vinculados
                    confirmations = []
                    if "nodes" in data and isinstance(data["nodes"], dict):
                        for node_name, node_info in data["nodes"].items():
                            if isinstance(node_info, dict) and node_info.get(
                                "confirmed"
                            ):
                                # Recupera os IDs dos alertas diretamente das janelas ou metadados
                                for key in ["alert_ids", "evidences"]:
                                    if key in node_info and isinstance(
                                        node_info[key], list
                                    ):
                                        confirmations.extend(node_info[key])

                    # Se a lista global for um dicionário (chave: objeto_alerta)
                    if isinstance(all_alerts, dict):
                        for aid in confirmations:
                            if aid in all_alerts:
                                al = all_alerts[aid]
                                if isinstance(al, dict):
                                    if "Alert ID" not in al and "id" not in al:
                                        al["Alert ID"] = aid
                                    alerts_list.append(al)
                        # Se as confirmações vieram vazias, importa todos os alertas disponíveis
                        if not alerts_list:
                            for aid, al in all_alerts.items():
                                if isinstance(al, dict):
                                    if "Alert ID" not in al and "id" not in al:
                                        al["Alert ID"] = aid
                                    alerts_list.append(al)
                    elif isinstance(all_alerts, list):
                        alerts_list = all_alerts

        except Exception as e:
            logger.error(f"Erro ao extrair contexto do grafo: {e}")

        # Normalização rigorosa das chaves para preencher as tabelas .tex
        normalized_alerts = []
        current_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        for idx, alert in enumerate(alerts_list):
            if not isinstance(alert, dict):
                continue

            ts = alert.get(
                "Timestamp",
                alert.get(
                    "timestamp",
                    alert.get("time", alert.get("TimeGenerated", current_time_str)),
                ),
            )
            aid = alert.get(
                "Alert ID",
                alert.get(
                    "alert_id", alert.get("Number", alert.get("id", f"W11{idx+1}"))
                ),
            )
            cat = alert.get("Category", alert.get("category", "Security Event"))
            tier = alert.get("Tier", alert.get("tier", alert.get("severity", "HIGH")))
            phase = alert.get(
                "Kill Chain",
                alert.get("_computed_phase", alert.get("phase", "EXECUTION")),
            )

            # Captura IoCs e Ativos presentes nas propriedades do alerta bruto
            for key in ["Destination", "dst", "ip", "domain"]:
                if key in alert and alert[key]:
                    raw_iocs.add(str(alert[key]))
            for key in ["Computer", "host", "device", "asset"]:
                if key in alert and alert[key]:
                    raw_assets.add(str(alert[key]))

            normalized_alerts.append(
                {
                    "Timestamp": str(ts),
                    "Alert ID": str(aid),
                    "Category": str(cat).upper(),
                    "Tier": str(tier).upper(),
                    "Kill Chain": str(phase).upper(),
                }
            )

        # Injeção de Segurança (Garante que a tabela NUNCA fique em branco com vírgulas)
        if not normalized_alerts:
            logger.warning(
                "[GraphReporter] No alerts found for context — timeline will be empty"
            )

        sev_breakdown = {}
        for a in normalized_alerts:
            sev = (a.get("Severity") or a.get("severity") or "").title()
            if sev:
                sev_breakdown[sev] = sev_breakdown.get(sev, 0) + 1

        # Garante IoCs mínimos se o parser falhar
        iocs = list(raw_iocs)
        assets = list(raw_assets)

        # ── Extrair fases detectadas dos alertas normalizados ─────────────
        _phase_order = [
            "RECON",
            "INITIAL_ACCESS",
            "EXECUTION",
            "PERSISTENCE",
            "LATERAL_MOVEMENT",
            "EXFILTRATION",
            "IMPACT",
        ]
        _seen_phases = []
        for a in normalized_alerts:
            ph = a.get("Kill Chain", "").upper()
            if ph and ph in _phase_order and ph not in _seen_phases:
                _seen_phases.append(ph)
        _seen_phases.sort(key=lambda p: _phase_order.index(p))

        return {
            "alerts": normalized_alerts,
            "severity_breakdown": sev_breakdown,
            "total_alerts": len(normalized_alerts),
            "iocs": iocs,
            "affected_assets": assets,
            "detected_cves": [],
            "phases": _seen_phases,
            "kill_chain_progress": {p: 1.0 for p in _seen_phases},
        }

    def _run_llm_enhancement(
        self, confirmed_sorted: List, context: Dict, raw_alerts: List
    ) -> Dict:
        llm_analysis = {}

        if not _HAS_LLM or not LLM_AVAILABLE:
            logger.debug("[GraphReporter] LLM not available, skipping enhancement")
            return llm_analysis

        try:
            enhancer = LLMEnhancer()

            if not enhancer.can_enhance():
                logger.debug("[GraphReporter] LLMEnhancer cannot enhance (disabled)")
                return llm_analysis

            top_hyp = confirmed_sorted[0]
            label = top_hyp[0]
            score = top_hyp[1]
            tier = top_hyp[3] if len(top_hyp) > 3 else "HIGH"

            # ── Extrair kill chain e fases do contexto ────────────────────────
            kc = context.get("kill_chain_progress", {})
            active_phases = [p for p, v in kc.items() if v > 0.3]
            if not active_phases:
                active_phases = context.get("phases", [])

            # ── Extrair IOCs e assets ─────────────────────────────────────────
            ioc_bundle_data = {}
            if raw_alerts and _HAS_ANALYZERS:
                try:
                    ioc_bundle_data = DataExtractor.extract_ioc_bundle(raw_alerts)
                except Exception:
                    pass
            iocs_all = (
                ioc_bundle_data.get("ipv4_addresses", [])
                + ioc_bundle_data.get("fqdns", [])
                + ioc_bundle_data.get("executables", [])
            )[:20]
            assets_all = (
                DataExtractor.extract_assets(raw_alerts)
                if (raw_alerts and _HAS_ANALYZERS)
                else context.get("affected_assets", [])
            )
            cves_all = (
                DataExtractor.extract_cves(raw_alerts)
                if (raw_alerts and _HAS_ANALYZERS)
                else context.get("detected_cves", [])
            )

            # ── Determinar highest tier ───────────────────────────────────────
            tier_order = {
                "CRITICAL": 0,
                "HIGH": 1,
                "MEDIUM-HIGH": 2,
                "MEDIUM": 3,
                "LOW-MED": 4,
                "LOW": 5,
            }
            highest_tier = tier
            for _, _, _, t, _ in confirmed_sorted:
                if tier_order.get(t, 5) < tier_order.get(highest_tier, 5):
                    highest_tier = t

            # ── Construir ciso_data e soc_data com contexto real ─────────────
            regulatory = self._get_regulatory_impact(highest_tier)
            top_categories = [
                [label, round(s, 4)] for _, s, _, _, _ in confirmed_sorted[:5]
            ]

            temp_ciso = {
                "top_risk_tier": highest_tier,
                "attack_pattern": label,
                "kill_chain_description": " → ".join(active_phases),
                "incident_status": "CONFIRMED",
                "top_categories": top_categories,
                "regulatory_impact": regulatory,
                "phase_score": context.get("phase_score", 0),
            }

            temp_soc = {
                "kill_chain_phases": active_phases,
                "total_alerts": len(raw_alerts) or context.get("total_alerts", 0),
                "total_triggers": len(confirmed_sorted),
                "iocs": iocs_all,
                "affected_assets": assets_all,
                "detected_cves": cves_all,
                "ioc_bundle": ioc_bundle_data,
            }

            lightweight_report = {
                "metadata": context,
                "selected_hypothesis": {"label": label, "probability": score},
            }

            enhanced_ciso, enhanced_soc = enhancer.enhance(
                temp_ciso, temp_soc, lightweight_report
            )
            model_value = enhancer.get_last_model_used()
            logger.info(
                f"[DEBUG] LLM model captured: {model_value}"
            )  # ← ADICIONAR ESTA LINHA

            llm_analysis = {
                "executive_summary": enhanced_ciso.get("executive_summary", ""),
                "recommended_actions": enhanced_ciso.get(
                    "strategic_recommendations", []
                )
                or enhanced_ciso.get("immediate_actions", []),
                "business_impact": enhanced_ciso.get("business_impact", ""),
                "regulatory_impact": enhanced_ciso.get("regulatory_impact", {}),
                "why_it_matters": enhanced_ciso.get("why_it_matters", ""),
                "what_was_detected": enhanced_ciso.get("what_was_detected", ""),
                "key_message": enhanced_ciso.get("key_message", ""),
                "analyst_assessment": enhanced_ciso.get("analyst_assessment", ""),
                "business_criticality": enhanced_ciso.get("business_criticality", {}),
                "threat_classification": enhanced_soc.get("threat_classification", ""),
                "containment_steps": enhanced_soc.get("containment_steps", []),
                "investigation_queries": enhanced_soc.get("investigation_queries", []),
                "priority_actions": enhanced_soc.get("priority_actions", {}),
                "model_used": model_value,
            }
            logger.info(f"[DEBUG] Final llm_analysis keys: {llm_analysis.keys()}")
            logger.info(
                f"[DEBUG] Final model_used value: {llm_analysis.get('model_used')}"
            )
            logger.info(
                f"[GraphReporter] LLM analysis complete. Provider: {LLM_PROVIDER}"
            )

        except Exception as exc:
            logger.warning(
                f"[GraphReporter] LLM enhancement failed: {exc} — using fallback"
            )

        # Construir executive_summary a partir dos campos LLM se não existir
        if not llm_analysis.get("executive_summary"):
            _what = llm_analysis.get("what_was_detected", "")
            _why = llm_analysis.get("why_it_matters", "")
            _key = llm_analysis.get("key_message", "")
            combined = " ".join(filter(None, [_what, _why]))
            if not combined:
                combined = _key
            if combined:
                llm_analysis["executive_summary"] = combined

        return llm_analysis

    def _generate_ciso_report(
        self, confirmed: List[Tuple[str, float, float, str, str]], context: Dict
    ) -> Dict:
        confirmed_sorted = sorted(confirmed, key=lambda x: -x[1])
        _window_id = ""
        try:
            graph = self._get_graph()
            if graph is not None:
                state = graph.get_graph_state()
                top_label = confirmed_sorted[0][0] if confirmed_sorted else ""
                for node in state.get("nodes", []):
                    if node.get("label") == top_label:
                        _window_id = node.get("window_id", "")
                        break
        except Exception:
            pass

        methods = set(c[4] for c in confirmed_sorted)
        if "operator" in methods:
            primary_method = "operator_validation"
        elif "timeout" in methods:
            primary_method = "auto_timeout"
        else:
            primary_method = "auto_threshold"

        if len(confirmed_sorted) == 1:
            label, score, _, tier, method = confirmed_sorted[0]
            method_desc = {
                "auto": "automatic threshold",
                "operator": "operator validation",
                "timeout": "automatic timeout",
            }.get(method, "algorithmic")
            exec_summary = (
                f"**{label}** has been confirmed with {score*100:.1f}% confidence "
                f"(Risk: {tier}). Confirmation method: {method_desc}."
            )
        else:
            labels = [
                f"**{label}** ({score*100:.1f}%)"
                for label, score, _, _, _ in confirmed_sorted[:3]
            ]
            exec_summary = f"Multiple hypotheses confirmed: {', '.join(labels)}. "

        kc = context.get("kill_chain_progress", {})
        active_phases = [p for p, v in kc.items() if v > 0.3]

        if not active_phases:
            active_phases = context.get("phases", [])

        if active_phases:
            exec_summary += f" Active kill chain phases: {' → '.join(active_phases)}."
        else:
            exec_summary += " No active kill chain phases detected."

        highest_tier = "LOW"
        tier_order = {
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM-HIGH": 2,
            "MEDIUM": 3,
            "LOW-MED": 4,
            "LOW": 5,
        }
        for _, _, _, tier, _ in confirmed_sorted:
            if tier_order.get(tier, 5) < tier_order.get(highest_tier, 5):
                highest_tier = tier

        recommendations = self._get_recommendations(
            highest_tier, confirmed_sorted, context
        )

        # ── Load real alerts for IOC/asset extraction ─────────────────────────
        raw_alerts: List[Dict] = []
        assets: List[str] = []
        cves: List[str] = []
        iocs: List[str] = []
        mitre_techniques: List[Dict] = []

        try:
            graph = self._get_graph()
            confirmed_labels = [c[0] for c in confirmed_sorted]

            if graph is not None:
                alert_ids = graph.get_alert_ids_for_confirmations(confirmed_labels)
                if alert_ids:
                    raw_alerts = AlertLoader.get_alerts_by_ids(alert_ids)
                    logger.info(
                        f"[GraphReporter] Loaded {len(raw_alerts)}/{len(alert_ids)} "
                        f"raw alerts for enrichment"
                    )

            if raw_alerts and _HAS_ANALYZERS:
                assets = DataExtractor.extract_assets(raw_alerts)
                cves = DataExtractor.extract_cves(raw_alerts)
                ioc_bundle = DataExtractor.extract_ioc_bundle(raw_alerts)
                iocs = (
                    ioc_bundle.get("ipv4_addresses", []) + ioc_bundle.get("fqdns", [])
                )[:20]
                logger.info(
                    f"[GraphReporter] Enrichment: "
                    f"{len(assets)} assets, {len(cves)} CVEs, {len(iocs)} IoCs"
                )

        except Exception as exc:
            logger.warning(f"[GraphReporter] Alert enrichment failed: {exc}")

        # Fallback to context data when AlertLoader returns nothing
        if not assets:
            assets = context.get("affected_assets", [])
        if not iocs:
            iocs = context.get("iocs", [])
        if not cves:
            cves = context.get("detected_cves", [])

        # ── LLM enrichment with security validations ─────────────────────────
        # MOVED: agora executado fora do bloco except, na posição correta
        llm_analysis = self._run_llm_enhancement(confirmed_sorted, context, raw_alerts)

        report = {
            "metadata": {
                "agent": "Agent 2 - Graph Reporter v2.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "output_timestamp": datetime.now(timezone.utc).isoformat(),
                "trigger": "hypothesis_confirmation",
                "confirmation_threshold": CONFIRMATION_THRESHOLD,
                "num_hypotheses_confirmed": len(confirmed),
                "confirmation_method": primary_method,
                "confirmed": True,
                "selected_hypothesis": _fmt_label(confirmed_sorted[0][0])
                if confirmed_sorted
                else "",
                "llm_used": LLM_AVAILABLE and _HAS_LLM and bool(llm_analysis),
                "model_used": llm_analysis.get("model_used", LLM_PROVIDER)
                if (LLM_AVAILABLE and _HAS_LLM)
                else "rule-based",
                # Window context — populated from evidence summary
                "window_id": _window_id or context.get("window_id", ""),
                "alert_count": context.get("total_alerts", 0),
                "phases": active_phases,  # context.get("phases", []),
                "phase_score": context.get("phase_score", 0),
                "window_start": context.get("window_start_ms", 0),
                "window_end": context.get("window_end_ms", 0),
            },
            "decision": {
                "selected_hypothesis": {
                    "label": _fmt_label(confirmed_sorted[0][0])
                    if confirmed_sorted
                    else "",
                    "probability": round(confirmed_sorted[0][1], 4)
                    if confirmed_sorted
                    else 0,
                    "risk_tier": confirmed_sorted[0][3] if confirmed_sorted else "—",
                }
                if confirmed_sorted
                else {},
                "decision_method": primary_method,
                "all_hypotheses": [
                    {"label": _fmt_label(l), "probability": round(s, 4)}
                    for l, s, _, _, _ in confirmed_sorted
                ],
            },
            "ciso_report": {
                "top_risk_tier": highest_tier,
                "executive_summary": llm_analysis.get(
                    "executive_summary", exec_summary
                ),
                "summary": llm_analysis.get("executive_summary", exec_summary),
                "primary_hypothesis": _fmt_label(confirmed_sorted[0][0])
                if confirmed_sorted
                else "",
                "primary_probability": round(confirmed_sorted[0][1], 4)
                if confirmed_sorted
                else 0,
                "top_categories": [
                    [_fmt_label(label), round(score, 4)]
                    for label, score, _, _, _ in confirmed_sorted[:5]
                ],
                "strategic_recommendations": (
                    llm_analysis.get("recommended_actions", []) or recommendations
                ),
                "regulatory_implications": " | ".join(
                    [
                        f"NIS2: {v}"
                        for k, v in (
                            llm_analysis.get("regulatory_impact")
                            or self._get_regulatory_impact(highest_tier)
                        ).items()
                        if v
                    ]
                ),
                "business_impact": llm_analysis.get("business_impact", ""),
                "why_it_matters": llm_analysis.get("why_it_matters", ""),
                "what_was_detected": llm_analysis.get("what_was_detected", ""),
                "key_message": llm_analysis.get("key_message", ""),
                "analyst_assessment": llm_analysis.get("analyst_assessment", ""),
                "business_criticality": llm_analysis.get("business_criticality", {}),
            },
            "soc_report": {
                "total_alerts": len(raw_alerts)
                or context.get("total_evidence_windows", 0),
                "affected_assets": assets,
                "mitre_techniques": [
                    t.get("id", "")
                    for t in (llm_analysis.get("mitre_techniques") or [])
                ],
                "kill_chain_phases": active_phases,
                "remediation_steps": llm_analysis.get(
                    "recommended_actions", recommendations
                ),
                "ioc_bundle": {
                    "ipv4_addresses": list(
                        dict.fromkeys(
                            i for i in iocs if re.match(r"\d+\.\d+\.\d+\.\d+", i)
                        )
                    ),
                    "fqdns": list(
                        dict.fromkeys(
                            i
                            for i in iocs
                            if "." in i
                            and not re.match(r"\d+\.\d+\.\d+\.\d+", i)
                            and "/" not in i
                            and ":" not in i
                        )
                    ),
                    "executables": list(
                        dict.fromkeys(
                            i
                            for i in iocs
                            if i.endswith(".exe")
                            or i.endswith(".dll")
                            or i.endswith(".bat")
                            or i.endswith(".ps1")
                        )
                    ),
                    "cve_ids": list(dict.fromkeys(cves)),
                },
                # Raw alerts for timeline generation in LaTeX
                "raw_alerts": raw_alerts,
                "trigger_events": [
                    {
                        "timestamp": datetime.fromtimestamp(
                            (a.get("_timestamp_ms") or a.get("timestamp_ms") or 0)
                            / 1000,
                            tz=timezone.utc,
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "id": str(a.get("Number") or a.get("number") or "—"),
                        "category": a.get("Category") or a.get("category") or "—",
                        "tier": a.get("RiskTier") or a.get("risk_tier") or "—",
                        "kill_chain": a.get("KillChain")
                        or a.get("kill_chain")
                        or a.get("Phase")
                        or a.get("phase")
                        or "—",
                    }
                    for a in raw_alerts
                ],
                "threat_classification": llm_analysis.get("threat_classification", ""),
                "containment_steps": llm_analysis.get("containment_steps", []),
                "investigation_queries": llm_analysis.get("investigation_queries", []),
            },
            "executive_summary": llm_analysis.get("executive_summary", exec_summary),
            "confirmed_hypotheses": [
                {
                    "label": label,
                    "confidence": round(score, 4),
                    "confidence_percent": round(score * 100, 1),
                    "risk_tier": tier,
                    "confirmed_by": method,
                    "confirmed_at": datetime.fromtimestamp(
                        ts / 1000, tz=timezone.utc
                    ).isoformat(),
                }
                for label, score, ts, tier, method in confirmed_sorted
            ],
            # Flat list of label strings for frontend badge matching
            "confirmed_hypothesis_labels": [
                label for label, _, _, _, _ in confirmed_sorted
            ],
            "kill_chain_progress": {
                phase: round(progress, 3) for phase, progress in kc.items()
            },
            "top_hypotheses": context.get("top_hypotheses", [])[:5],
            "recommended_actions": llm_analysis.get(
                "recommended_actions", recommendations
            ),
            "priority_actions": llm_analysis.get("priority_actions", {}),
            "regulatory_impact": (
                llm_analysis.get("regulatory_impact")
                or self._get_regulatory_impact(highest_tier)
            ),
        }

        return report

    def _get_recommendations(
        self, highest_tier: str, confirmed: List, context: Dict
    ) -> List[str]:
        has_operator_confirmation = any(c[4] == "operator" for c in confirmed)

        if highest_tier == "CRITICAL":
            recommendations = [
                "🚨 **ACTIVATE INCIDENT RESPONSE PLAN IMMEDIATELY**",
                "Notify CERT within 24h (NIS2 Art. 23)",
                "Evaluate GDPR Art.33 notification (72h for personal data breach)",
                "Isolate affected systems and preserve forensic evidence",
                "Brief CISO and legal counsel",
                "Activate crisis communication protocol",
            ]
        elif highest_tier == "HIGH":
            recommendations = [
                "**ESCALATE TO CISO AND IR TEAM** within 1 hour",
                "Review and restrict privileged access for affected assets",
                "Prepare incident report for management",
                "Increase monitoring frequency for related indicators",
                "Document findings in breach register per GDPR Art.33(5)",
            ]
        elif highest_tier == "MEDIUM-HIGH":
            recommendations = [
                "Initiate formal investigation within 4 hours",
                "Increase monitoring frequency",
                "Review detection rules based on confirmed TTPs",
                "Document for quarterly risk review",
                "Consider threat hunting for similar patterns",
            ]
        elif highest_tier == "MEDIUM":
            recommendations = [
                "Assign to L2 analyst within SLA",
                "Review asset baseline for anomalies",
                "Update threat hunting playbooks",
                "Document for trend analysis",
            ]
        else:
            recommendations = [
                "Continue standard monitoring",
                "Review detection rules based on observed patterns",
                "Update threat intelligence feeds",
                "Log for quarterly reporting",
            ]

        if has_operator_confirmation:
            recommendations.insert(
                0,
                "✓ **Operator validation received** - proceeding with confirmed classification",
            )

        return recommendations

    def _get_regulatory_impact(self, highest_tier: str) -> Dict[str, str]:
        regulatory = {
            "NIS2": "",
            "GDPR": "",
            "DORA": "",
        }

        if highest_tier == "CRITICAL":
            regulatory[
                "NIS2"
            ] = "Significant incident - notify CERT within 24h (Art. 23)"
            regulatory[
                "GDPR"
            ] = "Potential personal data breach - evaluate Art.33 notification within 72h"
            regulatory[
                "DORA"
            ] = "Major ICT incident - report to competent authority within 24h"
        elif highest_tier == "HIGH":
            regulatory[
                "NIS2"
            ] = "Evaluate significance threshold - prepare notification draft"
            regulatory[
                "GDPR"
            ] = "Document in breach register - evaluate notification requirement"
            regulatory["DORA"] = "Significant ICT incident - prepare report"
        elif highest_tier == "MEDIUM-HIGH":
            regulatory[
                "NIS2"
            ] = "Monitor evolution - notification conditional on confirmation"
            regulatory["GDPR"] = "Log internally per Art.33(5)"
            regulatory["DORA"] = "Monitor for escalation"
        else:
            regulatory["NIS2"] = "No immediate obligation - log for annual report"
            regulatory["GDPR"] = "No direct impact expected"
            regulatory["DORA"] = "No immediate impact"

        return regulatory

    def _save_report(self, report: Dict, context: Dict = {}) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_id = f"graph_report_{timestamp}"
        AGENT2_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # ── Generate LaTeX (CISO + SOC) ───────────────────────────────────────
        if _HAS_LATEX:
            try:
                soc = report.get("soc_report", {})
                ciso = report.get("ciso_report", {})
                decision = report.get("decision", {})
                meta = report.get("metadata", {})

                # ── Alert timeline from raw_alerts in soc_report ─────────────
                raw_alerts_list = (
                    soc.get("raw_alerts")
                    or soc.get("alerts")
                    or context.get("alerts")
                    or []
                )
                # ── Window timestamps ────────────────────────────────────────
                w_start_ms = (
                    meta.get("window_start_ms")
                    or meta.get("window_start")
                    or context.get("window_start_ms")
                    or 0
                )
                w_end_ms = (
                    meta.get("window_end_ms")
                    or meta.get("window_end")
                    or context.get("window_end_ms")
                    or 0
                )

                # Fallback: usa timestamps dos alertas se window timestamps estão a zero
                if not w_start_ms and raw_alerts_list:
                    ts_values = [
                        a.get("_timestamp_ms") or a.get("timestamp_ms") or 0
                        for a in raw_alerts_list
                    ]
                    ts_values = [t for t in ts_values if t > 0]
                    if ts_values:
                        w_start_ms = min(ts_values)
                        w_end_ms = max(ts_values)

                w_start_str = (
                    datetime.fromtimestamp(w_start_ms / 1000, tz=timezone.utc).strftime(
                        "%H:%M"
                    )
                    if w_start_ms
                    else "—"
                )
                w_end_str = (
                    datetime.fromtimestamp(w_end_ms / 1000, tz=timezone.utc).strftime(
                        "%H:%M"
                    )
                    if w_end_ms
                    else "—"
                )

                # ── Alert timeline from raw_alerts in soc_report ─────────────
                timeline = []
                detailed_timeline = []
                severity_counts: dict = {}

                # Phase → Tier mapping for display when RiskTier absent
                _PHASE_TIER = {
                    "IMPACT": "CRITICAL",
                    "EXFILTRATION": "HIGH",
                    "LATERAL_MOVEMENT": "HIGH",
                    "PERSISTENCE": "MEDIUM-HIGH",
                    "EXECUTION": "MEDIUM-HIGH",
                    "INITIAL_ACCESS": "MEDIUM",
                    "RECON": "LOW",
                    "UNKNOWN": "—",
                }
                for a in raw_alerts_list:
                    sev = (a.get("Severity") or a.get("severity") or "Unknown").title()
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                    ts_ms = a.get("_timestamp_ms") or a.get("timestamp_ms") or 0
                    ts_str = (
                        datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if ts_ms
                        else "—"
                    )
                    num_raw = a.get("Number") or a.get("number") or ""
                    num = str(num_raw) if num_raw else "—"
                    cat = a.get("Category") or a.get("category") or "—"
                    # Compute phase from Category/Type if not already present
                    kc = (
                        a.get("KillChain")
                        or a.get("kill_chain")
                        or a.get("Phase")
                        or a.get("phase")
                        or ""
                    ).upper()
                    if not kc or kc == "—":
                        try:
                            from agent1.mappings import get_phase_enriched

                            kc, _ = get_phase_enriched(a)
                        except Exception:
                            kc = "UNKNOWN"
                    tier = (
                        a.get("RiskTier")
                        or a.get("risk_tier")
                        or _PHASE_TIER.get(kc.upper(), "—")
                    )
                    timeline.append(
                        {
                            "timestamp": ts_str,
                            "id": num,
                            "category": cat,
                            "tier": tier,
                            "kill_chain": kc.lower(),
                        }
                    )
                    detailed_timeline.append(
                        {
                            "timestamp": ts_str,
                            "id": num,
                            "category": cat,
                            "severity": sev,
                            "kill_chain": kc.lower(),
                            "tier": tier,
                        }
                    )

                # Sort by timestamp
                timeline.sort(key=lambda x: x["timestamp"])
                detailed_timeline.sort(key=lambda x: x["timestamp"])

                # ── Trigger events (first alert per window) ──────────────────
                trigger_events = soc.get("trigger_events") or (
                    timeline[:1] if timeline else []
                )

                # ── Write window timestamps into metadata so LaTeX _format_timestamp finds them ──
                report["metadata"]["window_start_ms"] = w_start_ms or 0
                report["metadata"]["window_end_ms"] = w_end_ms or 0
                report["metadata"]["alert_count"] = meta.get("alert_count") or len(
                    raw_alerts_list
                )

                top_hyp_label = decision.get("selected_hypothesis", {})
                if isinstance(top_hyp_label, dict):
                    top_hyp_label = top_hyp_label.get("label", "")

                if "  " in top_hyp_label:
                    top_hyp_label = top_hyp_label.split("  ", 1)[1].strip()

                _phases = (
                    meta.get("phases", [])
                    or soc.get("kill_chain_phases", [])
                    or context.get("phases", [])
                    or list(
                        dict.fromkeys(
                            a.get("kill_chain", "").upper()
                            for a in detailed_timeline
                            if a.get("kill_chain")
                            and a.get("kill_chain").upper()
                            not in ("", "UNKNOWN", "---")
                        )
                    )
                )

                analysis = {
                    "executive_summary": ciso.get("executive_summary", ""),
                    "top_risk_tier": ciso.get("top_risk_tier", "—"),
                    "top_categories": ciso.get("top_categories", []),
                    "strategic_recommendations": ciso.get(
                        "strategic_recommendations", []
                    ),
                    "regulatory_impact": report.get("regulatory_impact", {}),
                    "business_impact": ciso.get("business_impact", ""),
                    "attack_pattern": top_hyp_label,
                    "label": top_hyp_label,
                    "incident_status": "CONFIRMED",
                    "confidence_level": f"{decision.get('selected_hypothesis',{}).get('probability',0)*100:.0f}%"
                    if isinstance(decision.get("selected_hypothesis"), dict)
                    else "—",
                    # LaTeX reads initial_vector and risk_explanation — not vector/risk_description
                    "initial_vector": " → ".join(_phases),
                    "kill_chain_description": " → ".join(_phases),
                    "risk_explanation": ciso.get("risk_description", "")
                    or ciso.get("top_risk_tier", "—"),
                    "why_it_matters": ciso.get("why_it_matters", ""),
                    "what_was_detected": ciso.get("what_was_detected", ""),
                    "key_message": ciso.get("key_message", "")
                    or f"{top_hyp_label} — {ciso.get('top_risk_tier','—')} risk confirmed.",
                    "active_kill_chains": len(soc.get("kill_chain_phases", [])),
                    "total_alerts": meta.get("alert_count")
                    or soc.get("total_alerts")
                    or len(raw_alerts_list),
                    "total_triggers": len(report.get("confirmed_hypotheses", [])),
                    # Timeline — CISO uses "timeline", SOC uses "detailed_timeline"
                    "timeline": detailed_timeline,  # CISO trigger timeline
                    "detailed_timeline": detailed_timeline,  # SOC full alert timeline
                    # IoCs — deduplicated
                    "iocs": context.get(
                        "iocs",
                        list(
                            dict.fromkeys(
                                soc.get("ioc_bundle", {}).get("ipv4_addresses", [])
                                + soc.get("ioc_bundle", {}).get("fqdns", [])
                                + soc.get("ioc_bundle", {}).get("executables", [])
                            )
                        ),
                    ),  # ← três parênteses: list(), dict.fromkeys(), context.get()
                    "affected_assets": context.get(
                        "affected_assets",
                        list(dict.fromkeys(soc.get("affected_assets", []))),
                    ),
                    "detected_cves": context.get(
                        "detected_cves",
                        list(
                            dict.fromkeys(soc.get("ioc_bundle", {}).get("cve_ids", []))
                        ),
                    ),
                    "severity_breakdown": severity_counts
                    or context.get("severity_breakdown", {}),
                    # SOC-level tactical recommendations derived from phases detected
                    "soc_recommendations": _soc_recs_from_phases(
                        soc.get("kill_chain_phases", []) or meta.get("phases", [])
                    ),
                    "recommended_actions": report.get("recommended_actions", []),
                    "technical_summary": report.get("executive_summary", "")
                    or ciso.get("executive_summary", ""),
                    "attack_vector_analysis": (
                        ciso.get("attack_vector_analysis")
                        or ciso.get("attack_vector")
                        or " → ".join(soc.get("kill_chain_phases", []))
                    ),
                    "phases": _phases,
                    "phase_score": meta.get("phase_score", 0),
                    "window_id": meta.get("window_id", ""),
                    # Campos adicionais para o LaTeX SOC
                    "threat_classification": soc.get("threat_classification", ""),
                    "containment_steps": soc.get("containment_steps", []),
                    "investigation_queries": soc.get("investigation_queries", []),
                    "window_start_ms": w_start_ms,
                    "window_end_ms": w_end_ms,
                    "priority_actions": report.get("priority_actions", {}),
                }

                ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                logger.info(
                    f"[GraphReporter] Generating CISO LaTeX → {report_id}_ciso.tex"
                )
                ciso_tex = CISOReportGenerator().generate(report, analysis, ts_str)
                ciso_tex_path = AGENT2_REPORTS_DIR / f"{report_id}_ciso.tex"
                ciso_tex_path.write_text(ciso_tex, encoding="utf-8")
                logger.info(f"[GraphReporter] CISO LaTeX saved: {ciso_tex_path}")

                logger.info(
                    f"[GraphReporter] Generating SOC LaTeX → {report_id}_soc.tex"
                )
                soc_tex = SOCReportGenerator().generate(report, analysis, ts_str)
                soc_tex_path = AGENT2_REPORTS_DIR / f"{report_id}_soc.tex"
                soc_tex_path.write_text(soc_tex, encoding="utf-8")
                logger.info(f"[GraphReporter] SOC LaTeX saved: {soc_tex_path}")

                # Write filenames into metadata so the dashboard card can find them
                report["metadata"]["tex_file"] = ciso_tex_path.name
                report["metadata"]["soc_tex_file"] = soc_tex_path.name
                # pdf_file is the ciso .tex name — texer compiles it on demand via /render-pdf
                report["metadata"]["pdf_file"] = ciso_tex_path.name

            except Exception as exc:
                logger.error(
                    f"[GraphReporter] LaTeX generation FAILED: {exc}", exc_info=True
                )
        else:
            logger.warning(
                "[GraphReporter] LaTeX skipped — latex_generator not available (_HAS_LATEX=False)"
            )

        # ── Save JSON ─────────────────────────────────────────────────────────
        json_path = AGENT2_REPORTS_DIR / f"{report_id}.json"
        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        # ── Save Markdown summary ─────────────────────────────────────────────
        md_lines = [
            "# CISO Intelligence Report",
            f"**Generated:** {report['metadata']['generated_at']}",
            f"**Method:** {report['metadata']['confirmation_method']}",
            f"**Hypothesis:** {report['metadata']['selected_hypothesis']}",
            "",
            "## Executive Summary",
            report.get("executive_summary", ""),
            "",
            "## Confirmed Hypotheses",
        ]
        for hyp in report.get("confirmed_hypotheses", []):
            md_lines.append(
                f"- **{hyp['label']}**: {hyp['confidence_percent']}% (Risk: {hyp['risk_tier']}) "
                f"— {hyp['confirmed_by']} at {hyp['confirmed_at'][:19]}"
            )

        md_path = AGENT2_REPORTS_DIR / f"{report_id}.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        logger.info(f"Report saved: {json_path.name}")

        with self._lock:
            self._generated_reports.insert(0, report)
            if len(self._generated_reports) > 50:
                self._generated_reports = self._generated_reports[:50]

        return json_path

    def _emit_report(self, report: Dict) -> bool:
        try:
            success = _emit_sse("ciso_report", report)
            if success:
                logger.info(
                    f"CISO report emitted to dashboard: {len(report['confirmed_hypotheses'])} hypotheses"
                )
            else:
                logger.warning("Failed to emit CISO report via SSE")
            return success
        except Exception as e:
            logger.error(f"Failed to emit report: {e}")
            return False

    def _auto_confirm_timeouts(self) -> None:
        graph = self._get_graph()
        if graph is None:
            return

        try:
            auto_confirmed = graph.auto_confirm_timeouts()
            if auto_confirmed:
                logger.info(
                    f"Auto-confirmed {len(auto_confirmed)} hypothesis(es) by timeout"
                )
                for label, score, tier in auto_confirmed:
                    logger.info(f"  - {label}: {score*100:.1f}% ({tier})")
        except Exception as e:
            logger.error(f"Failed to auto-confirm timeouts: {e}")

    def _load_queue(self) -> dict:
        """Load pending queue from disk — restores reports queued before restart."""
        try:
            if self._QUEUE_FILE.exists():
                data = json.loads(self._QUEUE_FILE.read_text())
                logger.info(f"[Queue] Loaded {len(data)} pending report(s) from disk")
                return data
        except Exception as e:
            logger.warning(f"[Queue] Failed to load queue: {e}")
        return {}

    def _save_queue(self) -> None:
        """Persist queue to disk atomically."""
        try:
            self._QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._QUEUE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._pending_queue, ensure_ascii=False))
            tmp.replace(self._QUEUE_FILE)
        except Exception as e:
            logger.warning(f"[Queue] Failed to save queue: {e}")

    def _enqueue(
        self, label: str, score: float, ts: float, tier: str, method: str
    ) -> None:
        """Add a confirmed hypothesis to the pending queue."""
        with self._queue_lock:
            if label not in self._pending_queue:
                self._pending_queue[label] = {
                    "label": label,
                    "score": score,
                    "ts": ts,
                    "tier": tier,
                    "method": method,
                    "attempts": 0,
                    "queued_at": datetime.now(timezone.utc).isoformat(),
                }
                self._save_queue()
                logger.info(f"[Queue] Enqueued: {label} ({method})")
            else:
                logger.debug(f"[Queue] Already queued: {label}")

    def _dequeue_success(self, label: str) -> None:
        """Remove from queue after successful report generation and emit."""
        with self._queue_lock:
            if label in self._pending_queue:
                del self._pending_queue[label]
                self._save_queue()
                logger.info(f"[Queue] Completed: {label}")

    def _process_queue(self) -> None:
        """Process all pending queued reports — called from poll loop."""
        with self._queue_lock:
            pending = list(self._pending_queue.values())

        if not pending:
            return

        logger.info(f"[Queue] Processing {len(pending)} pending report(s)")

        def _gen(entry: dict) -> None:
            label = entry["label"]
            try:
                with self._queue_lock:
                    if label in self._pending_queue:
                        self._pending_queue[label]["attempts"] += 1
                        self._save_queue()

                context = self._get_graph_context()
                confirmations = [
                    (label, entry["score"], entry["ts"], entry["tier"], entry["method"])
                ]
                report = self._generate_ciso_report(confirmations, context)
                self._save_report(report, context)
                ok = self._emit_report(report)
                if ok:
                    self._dequeue_success(label)
                    self._processed_confirmations.add(label)
                    self._last_processed_confirmation_ms = max(
                        entry["ts"], self._last_processed_confirmation_ms
                    )
                    logger.info(f"[Queue] ✓ Report emitted: {label}")
                else:
                    logger.warning(f"[Queue] Emit failed for {label} — will retry")
            except Exception as e:
                logger.error(
                    f"[Queue] Generation failed for {label}: {e}", exc_info=True
                )
                # Leave in queue for next poll cycle retry

        # Run in parallel if multiple pending
        if len(pending) == 1:
            _gen(pending[0])
        else:
            threads = [
                threading.Thread(
                    target=_gen, args=(e,), daemon=True, name=f"queue-{e['label'][:16]}"
                )
                for e in pending
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=AGENT2_TIMEOUT_SECONDS + 10)

    def trigger_report_now(
        self, label: str, score: float, ts: float, tier: str, method: str
    ) -> bool:
        """
        Called by sse_server after operator confirmation.
        Enqueues immediately and attempts generation — if generation fails,
        the queue guarantees retry on next poll cycle.
        """
        # Enqueue first — guarantees the report will eventually be generated
        self._enqueue(label, score, ts, tier, method)

        # Attempt immediate generation
        logger.info(f"[GraphReporter] Immediate report attempt: {label} ({method})")
        try:
            context = self._get_graph_context()
            confirmations = [(label, score, ts, tier, method)]
            report = self._generate_ciso_report(confirmations, context)
            self._save_report(report, context)
            ok = self._emit_report(report)
            if ok:
                self._dequeue_success(label)
                self._processed_confirmations.add(label)
                self._last_processed_confirmation_ms = max(
                    ts, self._last_processed_confirmation_ms
                )
                logger.info(f"[GraphReporter] ✓ Report generated immediately: {label}")
                return True
            else:
                logger.warning(
                    f"[GraphReporter] Emit failed — queued for retry: {label}"
                )
                return False
        except Exception as exc:
            logger.error(
                f"[GraphReporter] Immediate generation failed — queued for retry: {exc}"
            )
            return False

    def run(self) -> None:
        logger.info("Starting Graph Reporter...")
        logger.info("Waiting for hypothesis confirmations from the graph")

        self._running = True
        # Start from 0 — deduplication is handled by _processed_confirmations set,
        # not by timestamp comparison. Starting from now() caused operator
        # confirmations to be missed when confirmation_time_ms <= startup_time_ms.
        self._last_processed_confirmation_ms = 0

        try:
            while self._running:
                self._auto_confirm_timeouts()
                confirmations = self._get_new_confirmations()

                # Enqueue any new confirmations not yet queued
                if confirmations:
                    for label, score, ts, tier, method in confirmations:
                        if label not in self._processed_confirmations:
                            self._enqueue(label, score, ts, tier, method)
                    try:
                        max_ts = max(ts for _, _, ts, _, _ in confirmations)
                        self._last_processed_confirmation_ms = max(
                            max_ts, self._last_processed_confirmation_ms
                        )
                    except Exception:
                        pass

                # Process all queued reports — new + any previous failures
                self._process_queue()

                time.sleep(self._poll_interval)

        except KeyboardInterrupt:
            logger.info("Agent 2 stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in Graph Reporter: {e}", exc_info=True)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        logger.info("Graph Reporter stopping")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Agent 2 - Graph Reporter")
    parser.add_argument("--poll-interval", type=int, default=2)
    parser.add_argument("--once", action="store_true")

    # parse_known_args prevents crash when launched via importlib with launcher argv
    args, _ = parser.parse_known_args()

    reporter = GraphReporter(poll_interval=args.poll_interval)
    _set_global_reporter(reporter)

    if args.once:
        reporter._last_processed_confirmation_ms = 0
        confirmations = reporter._get_new_confirmations()
        if confirmations:
            context = reporter._get_graph_context()
            report = reporter._generate_ciso_report(confirmations, context)
            reporter._save_report(report, context)
            logger.info(json.dumps(report, indent=2))
        else:
            logger.warning("No confirmations found")
    else:
        reporter.run()


# ── Global reporter singleton — allows sse_server to trigger reports directly ─
_global_reporter: Optional["GraphReporter"] = None
_reporter_lock = threading.Lock()


def _set_global_reporter(reporter: "GraphReporter") -> None:
    global _global_reporter
    with _reporter_lock:
        _global_reporter = reporter


def get_global_reporter() -> Optional["GraphReporter"]:
    with _reporter_lock:
        return _global_reporter


if __name__ == "__main__":
    main()
