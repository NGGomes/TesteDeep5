"""
Analyzers for Agent 2 - CISO and SOC report generation.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set, Any
from pathlib import Path

import sys

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import AGENT2_REPORTS_DIR
from agent1.mappings import PHASE_PRIORITY

_PRIVATE_IP_RE = re.compile(
    r"^("
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"127\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"169\.254\.\d{1,3}\.\d{1,3}|"
    r"0\.0\.0\.0|"
    r"255\.255\.255\.255"
    r")$"
)

_TIER_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM-HIGH": 2,
    "MEDIUM": 3,
    "LOW-MED": 4,
    "LOW": 5,
    "—": 6,
}

_CONFIDENCE_TABLE: List[Tuple[int, int, str]] = [
    (30, 6, "HIGH"),
    (20, 5, "HIGH"),
    (15, 5, "MEDIUM"),
    (15, 3, "MEDIUM"),
    (10, 4, "MEDIUM"),
    (10, 2, "MEDIUM"),
    (6, 3, "MEDIUM"),
    (6, 1, "LOW"),
    (3, 1, "LOW"),
    (0, 0, "LOW"),
]


class DataExtractor:
    ASSET_FIELDS = [
        "AffectedAsset",
        "Affected Asset",
        "Asset",
        "HostName",
        "Host",
        "IP",
    ]

    @classmethod
    def extract_iocs(
        cls, alerts: List[dict], extra_alerts: Optional[List[dict]] = None
    ) -> List[str]:
        all_alerts = list(alerts) + (extra_alerts or [])
        try:
            from ioc_extractor import extract_iocs_from_alerts

            bundle = extract_iocs_from_alerts(all_alerts)
            return (bundle.ipv4_addresses + bundle.ipv6_addresses + bundle.fqdns)[:30]
        except ImportError:
            return cls._extract_iocs_inline(all_alerts)

    @classmethod
    def _extract_iocs_inline(cls, alerts: List[dict]) -> List[str]:
        _IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
        _URL_RE = re.compile(r"https?://[^\s\"'<>]+")
        text = json.dumps(alerts)
        iocs: Set[str] = set()
        for addr in _IP_RE.findall(text):
            if not cls._is_private_ip(addr):
                iocs.add(addr)
        for url in _URL_RE.findall(text):
            iocs.add(url)
        return list(iocs)[:30]

    @classmethod
    def _is_private_ip(cls, addr: str) -> bool:
        return bool(_PRIVATE_IP_RE.match(addr))

    @classmethod
    def extract_cves(
        cls, alerts: List[dict], extra_cves: Optional[List[str]] = None
    ) -> List[str]:
        _CVE_RE = re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE)
        text = json.dumps(alerts)
        cves: Set[str] = set(_CVE_RE.findall(text))
        if extra_cves:
            cves.update(c.upper() for c in extra_cves if c.upper())
        return sorted(cves)[:20]

    @classmethod
    def extract_ioc_bundle(
        cls, alerts: List[dict], extra_alerts: Optional[List[dict]] = None
    ) -> dict:
        all_alerts = list(alerts) + (extra_alerts or [])
        try:
            from ioc_extractor import extract_iocs_from_alerts

            bundle = extract_iocs_from_alerts(all_alerts)
            result = bundle.as_dict()
        except ImportError:
            result = {
                "ipv4_addresses": [],
                "ipv6_addresses": [],
                "fqdns": [],
                "cve_ids": [],
                "total_iocs": 0,
            }

        result["has_external_iocs"] = (
            len(result.get("ipv4_addresses", [])) + len(result.get("fqdns", [])) > 0
        )
        result["has_cves"] = len(result.get("cve_ids", [])) > 0
        result["threat_indicators"] = {
            "suspicious_ips": len(result.get("ipv4_addresses", [])),
            "malicious_domains": len(result.get("fqdns", [])),
            "known_vulnerabilities": len(result.get("cve_ids", [])),
        }
        return result

    @classmethod
    def extract_assets(
        cls, alerts: List[dict], triggers: Optional[List[dict]] = None
    ) -> List[str]:
        assets: Set[str] = set()
        for alert in alerts:
            for field in cls.ASSET_FIELDS:
                if alert.get(field):
                    assets.add(str(alert[field]))
        for trigger in triggers or []:
            for alert in trigger.get(
                "alerts_sequence", trigger.get("alert_sequence", [])
            ):
                for field in cls.ASSET_FIELDS:
                    if alert.get(field):
                        assets.add(str(alert[field]))
        return list(assets)[:30]

    @classmethod
    def extract_severity_breakdown(cls, alerts: List[dict]) -> Dict[str, int]:
        severity_counts: Dict[str, int] = defaultdict(int)
        for alert in alerts:
            severity = alert.get("Severity", alert.get("severity", "Unknown"))
            severity_counts[severity] += 1
        _tier_order = ["CRITICAL", "HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW-MED", "LOW"]
        return dict(
            sorted(
                severity_counts.items(),
                key=lambda x: _tier_order.index(x[0]) if x[0] in _tier_order else 99,
            )
        )


class TimelineBuilder:
    @staticmethod
    def build(
        triggers: List[dict], max_items: int = 20, include_kill_chain: bool = False
    ) -> List[dict]:
        timeline = []
        for trigger in triggers:
            item = TimelineBuilder._extract_base_item(trigger)
            if include_kill_chain:
                kc_raw = trigger.get("kill_chain", "")
                if isinstance(kc_raw, dict):
                    kc_phase = kc_raw.get("phase", "")
                else:
                    kc_phase = kc_raw if (kc_raw and kc_raw != "—") else ""
                if not kc_phase:
                    phases = trigger.get("phases_detected", [])
                    kc_phase = phases[0] if phases else ""
                item["kill_chain_phase"] = kc_phase
            timeline.append(item)

        unique_items = {}
        for item in timeline:
            dedup_key = f"{item.get('ts', '')}|{item.get('alert_id', '')}"
            if dedup_key not in unique_items:
                unique_items[dedup_key] = item

        sorted_items = sorted(unique_items.values(), key=lambda x: x.get("ts", ""))
        return sorted_items[:max_items]

    @staticmethod
    def _extract_base_item(trigger: dict) -> dict:
        trigger_alert = trigger.get("trigger_alert") or {}
        ciso_categories = trigger.get("ciso_categories", [{}])

        ts_ms = (
            trigger.get("trigger_ts_ms")
            or trigger_alert.get("timestamp_ms")
            or trigger.get("window_start_ms")
        )
        ts_str = ""
        if ts_ms:
            try:
                ts_str = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                ts_str = str(ts_ms)

        first_seq_alert = (
            trigger.get("alerts_sequence", trigger.get("alert_sequence", [{}]))[0]
            if trigger.get("alerts_sequence", trigger.get("alert_sequence", []))
            else {}
        )

        alert_id = (
            trigger.get("trigger_alert_id")
            or trigger_alert.get("Number")
            or trigger_alert.get("number")
            or first_seq_alert.get("Number")
            or first_seq_alert.get("number")
            or trigger_alert.get("ExternalId")
            or trigger_alert.get("external_id")
            or first_seq_alert.get("ExternalId")
            or first_seq_alert.get("external_id")
            or trigger_alert.get("id")
            or trigger_alert.get("alert_id")
            or trigger.get("Number")
            or trigger.get("ExternalId")
            or trigger.get("alert_id")
            or trigger.get("id")
            or trigger.get("event_id")
            or trigger.get("sequence_id")
            or "—"
        )

        return {
            "ts": ts_str,
            "ts_ms": ts_ms,
            "alert_id": str(alert_id),
            "ciso_category": ciso_categories[0].get("ciso_category_name", "")
            if ciso_categories
            else "",
            "risk_tier": ciso_categories[0].get("risk_tier", "—")
            if ciso_categories
            else "—",
        }


def resolve_primary_phase(
    primary_ciso_category: str, kill_chain_phases_detected: List[str]
) -> str:
    if not kill_chain_phases_detected:
        return "UNKNOWN"

    sorted_phases = sorted(
        kill_chain_phases_detected, key=lambda p: PHASE_PRIORITY.get(p, 99)
    )
    return sorted_phases[0]


def compute_confidence(score: float, n_kill_chain_phases: int) -> str:
    for min_score, min_phases, level in _CONFIDENCE_TABLE:
        if score >= min_score and n_kill_chain_phases >= min_phases:
            return level
    return "LOW"


class DashboardReportFormatter:
    """
    Formata e estrutura os relatórios analíticos para garantir
    compatibilidade absoluta com a interface visual (UI) do Dashboard SOC.
    """

    @staticmethod
    def format_for_dashboard(
        incident_id: str,
        label: str,
        score: float,
        tier: str,
        method: str,
        alerts: List[dict],
        llm_response_text: str,
    ) -> dict:
        raw_text = str(llm_response_text)

        # Divide inteligentemente a resposta do LLM caso use títulos Markdown (###)
        parts = raw_text.split("###")
        exec_summary = (
            parts[0].strip()
            if len(parts) > 0
            else f"Incidente crítico classificado como {label}."
        )

        # Se houver mais divisões, assume o resto como análise tática detalhada
        tactical_an = raw_text if len(parts) <= 1 else "\n".join(parts[1:]).strip()

        # Extração automática de metadados para popular os cartões da UI
        assets_extracted = DataExtractor.extract_assets(alerts)
        cves_extracted = DataExtractor.extract_cves(alerts)

        return {
            "incident_id": str(incident_id),
            "label": str(label),
            "score": float(score),
            "tier": str(tier),
            "method": str(method),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # CHAVES QUE O DASHBOARD PROCURA PARA PREENCHER OS CAMPOS VAZIOS:
            "executive_summary": exec_summary
            if exec_summary
            else f"Análise automatizada para {label}.",
            "tactical_analysis": tactical_an if tactical_an else raw_text,
            "mitre_matrix": {
                "tactics": [
                    alert.get("_computed_phase", "UNKNOWN")
                    for alert in alerts
                    if alert.get("_computed_phase")
                ],
                "techniques": [
                    alert.get("MitreAttack", "—")
                    for alert in alerts
                    if alert.get("MitreAttack")
                ],
            },
            "affected_assets": [
                {"asset": a, "type": "Host" if not _PRIVATE_IP_RE.match(a) else "IP"}
                for a in assets_extracted
            ],
            "detected_cves": list(cves_extracted),
            "alerts": alerts,
        }
