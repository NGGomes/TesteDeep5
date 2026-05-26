from __future__ import annotations

"""
Agent 2 - LLM-powered 360° Incident Analysis
"""

import json
import logging
import os
import sys
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any


_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent2.analyzers import DataExtractor

from shared_config import (
    LLM_PROVIDER2,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OPENAI_API_KEY,
    LITELLM_MODEL2,
    AGENT2_TIMEOUT_SECONDS,
    AGENT2_MAX_TOKENS,
    AGENT2_TEMPERATURE,
)

from core.logging import get_logger

_log = get_logger("agent2.llm_engine")

from agent2.llm_quality import (
    get_llm_cache,
    get_quality_metrics,
    get_complexity_calculator,
    get_cot_generator,
)
from shared_config import (
    LLM_CACHE_ENABLED,
    LLM_COT_ENABLED,
    LLM_QUALITY_METRICS_ENABLED,
    LLM_CROSS_VALIDATION,
    LLM_COMPLEXITY_HIGH,
    LLM_COMPLEXITY_MEDIUM,
)

# ============================================================================
# CONSTANTES DE SEGURANÇA
# ============================================================================

# Regex para detetar linguagem de breach não confirmada
_BREACH_INDICATORS = re.compile(
    r"\b(breach(ed)?|compromised our|exfiltrat(ed|ion)|confirmed data loss|"
    r"data stolen|systems? taken over|fully compromised)\b",
    re.IGNORECASE,
)

# Keys permitidas para LLM CISO (whitelist)
_CISO_LLM_ALLOWED_KEYS = {
    "why_it_matters",
    "what_was_detected",
    "immediate_actions",
    "key_message",
    "analyst_assessment",
    "business_criticality",
    "business_impact",
}

# Keys permitidas para LLM SOC (whitelist)
_SOC_LLM_ALLOWED_KEYS = {
    "threat_classification",
    "containment_steps",
    "investigation_queries",
    "priority_actions",
}


def _is_private_ip(addr: str) -> bool:
    """Verifica se um endereço IP é privado (não deve ser bloqueado)."""
    private_pattern = re.compile(
        r"^(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"127\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"169\.254\.\d{1,3}\.\d{1,3}|"
        r"0\.0\.0\.0|"
        r"255\.255\.255\.255)$"
    )
    return bool(private_pattern.match(addr))


# ============================================================================
# LLM CONFIGURATION
# ============================================================================

LLM_PROVIDER = LLM_PROVIDER2
LLM_AVAILABLE = False
LLM_ENABLED = LLM_PROVIDER != "none"

if LLM_ENABLED:
    try:
        import litellm

        LLM_AVAILABLE = True
        _log.info(f"[Agent2] LiteLLM loaded. Provider: {LLM_PROVIDER}")
    except ImportError:
        LLM_ENABLED = LLM_AVAILABLE = False
        _log.warning("[Agent2] LiteLLM not installed")

# Configure LiteLLM logging
LITELLM_LOG_LEVEL = os.getenv("LITELLM_LOG", "ERROR").upper()
os.environ["LITELLM_LOG"] = LITELLM_LOG_LEVEL

if LLM_AVAILABLE:
    logging.getLogger("litellm").setLevel(
        getattr(logging, LITELLM_LOG_LEVEL, logging.ERROR)
    )


def _get_llm_kwargs() -> dict:
    """Get LLM configuration based on provider"""
    if LLM_PROVIDER == "ollama":
        return {
            "model": f"ollama/{OLLAMA_MODEL}",
            "api_base": OLLAMA_BASE_URL,
            "api_key": "ollama",
        }
    elif LLM_PROVIDER == "anthropic":
        return {
            "model": f"anthropic/{ANTHROPIC_MODEL}",
            "api_key": ANTHROPIC_API_KEY,
        }
    else:  # openai or litellm default
        return {
            "model": LITELLM_MODEL2,
            "api_key": OPENAI_API_KEY or None,
        }


def _call_llm(prompt: str, max_tokens: int = 2000) -> Optional[str]:
    """Call LLM with timeout handling"""
    if not LLM_AVAILABLE or not LLM_ENABLED:
        return None

    import litellm

    try:
        kwargs = _get_llm_kwargs()
        kwargs.update(
            {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": AGENT2_TEMPERATURE,
                "max_tokens": max_tokens,
                "timeout": AGENT2_TIMEOUT_SECONDS,
            }
        )

        response = litellm.completion(**kwargs)

        usage = getattr(response, "usage", None)
        if usage:
            _log.debug("[Agent2] LLM tokens logged")

        return response.choices[0].message.content.strip()

    except Exception as e:
        _log.error(f"[Agent2] LLM call failed: {e}")
        return None


# ============================================================================
# LLM ENHANCER (com validações de segurança e melhorias)
# ============================================================================


class LLMEnhancer:
    """Enhanced LLM handler with cache, COT, quality metrics and dynamic model selection."""

    def __init__(self):
        self.enabled = LLM_ENABLED and LLM_AVAILABLE
        self.provider = LLM_PROVIDER
        self.last_model_used = None
        self._cache = get_llm_cache() if LLM_CACHE_ENABLED else None
        self._metrics = get_quality_metrics() if LLM_QUALITY_METRICS_ENABLED else None
        self._complexity = get_complexity_calculator()
        self._cot = get_cot_generator()

    def can_enhance(self) -> bool:
        return self.enabled

    def _get_llm_kwargs(self, complexity: float = 0.5) -> dict:
        """Get LLM configuration with dynamic model selection based on complexity."""
        if self.provider == "ollama":
            return {
                "model": f"ollama/{OLLAMA_MODEL}",
                "api_base": OLLAMA_BASE_URL,
                "api_key": "ollama",
            }
        elif self.provider == "anthropic":
            # Seleção dinâmica de modelo baseada na complexidade
            if LLM_CROSS_VALIDATION:
                model = self._complexity.select_model(complexity)
                if model == "claude-3-opus":
                    model_full = "anthropic/claude-3-opus-20240229"
                elif model == "claude-haiku":
                    model_full = f"anthropic/{ANTHROPIC_MODEL}"
                else:
                    model_full = f"anthropic/{ANTHROPIC_MODEL}"
            else:
                model_full = f"anthropic/{ANTHROPIC_MODEL}"

            return {
                "model": model_full,
                "api_key": ANTHROPIC_API_KEY,
            }
        else:
            return {
                "model": LITELLM_MODEL2,
                "api_key": OPENAI_API_KEY or None,
            }

    def get_last_model_used(self) -> str:
        """Retorna o último modelo LLM usado (ex: claude-3-sonnet-20240229)"""
        if self.last_model_used:
            model = self.last_model_used or ANTHROPIC_MODEL or "unknown"
            # Remove provider prefix if present
            if "/" in model:
                model = model.split("/", 1)[1]

            return model.strip()
        return ANTHROPIC_MODEL or "unknown"

    def _call_llm(
        self,
        prompt: str,
        max_tokens: int = 1500,
        context_hash: str = "",
        complexity: float = 0.5,
    ) -> Optional[str]:
        """Call LLM with caching and timeout handling."""
        if not self.can_enhance():
            return None

        # Verificar cache primeiro
        if self._cache and context_hash:
            cached = self._cache.get(prompt, context_hash)
            if cached:
                return cached

        import litellm
        import time

        start_time = time.time()

        try:
            kwargs = self._get_llm_kwargs(complexity)
            self.last_model_used = kwargs.get("model", ANTHROPIC_MODEL)
            _log.info(f"[DEBUG] LLM model set to: {self.last_model_used}")
            kwargs.update(
                {
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": AGENT2_TEMPERATURE,
                    "max_tokens": max_tokens,
                    "timeout": AGENT2_TIMEOUT_SECONDS,
                }
            )

            response = litellm.completion(**kwargs)
            result = response.choices[0].message.content.strip()

            # Armazenar em cache
            if self._cache and context_hash:
                self._cache.set(prompt, result, context_hash)

            # Registrar métricas de latência
            latency_ms = (time.time() - start_time) * 1000
            _log.debug(f"[Agent2] LLM call completed in {latency_ms:.0f}ms")

            return result

        except Exception as e:
            _log.error(f"[Agent2] LLM call failed: {e}")
            return None

    def _safe_merge_ciso(self, base: dict, llm_raw: dict, log: logging.Logger) -> dict:
        """Merge seguro para CISO - valida e filtra LLM output."""
        for key, value in llm_raw.items():
            if key not in _CISO_LLM_ALLOWED_KEYS:
                log.warning("LLM CISO: rejected key '%s' — not in allowed set.", key)
                continue

            # Rejeitar linguagem de breach não confirmada
            if key in ("key_message", "what_was_detected", "why_it_matters"):
                if isinstance(value, str) and _BREACH_INDICATORS.search(value):
                    log.warning(
                        "LLM CISO: '%s' contains unconfirmed breach language — keeping algorithmic value.",
                        key,
                    )
                    continue

            # Validar immediate_actions: cada ação deve ter um owner
            if key == "immediate_actions" and isinstance(value, list):
                cleaned = []
                owner_pattern = re.compile(
                    r"( — | - |: |\(|"
                    r"\b(IR team|CERT|CISO|SOC|Legal|Board|Counsel|"
                    r"Incident Commander|Security Team|Management)\b)",
                    re.IGNORECASE,
                )
                for action in value:
                    if not isinstance(action, str):
                        continue
                    if owner_pattern.search(action):
                        cleaned.append(action)
                    else:
                        log.warning(
                            "LLM CISO: immediate_action item missing owner — dropped: %r",
                            action,
                        )
                if cleaned:
                    base[key] = cleaned
                else:
                    log.warning(
                        "LLM CISO: all immediate_action items lacked owners — field not updated."
                    )
                continue

            old = base.get(key)
            if old != value:
                log.info(
                    "LLM CISO: merging '%s' (was %r → now %r).",
                    key,
                    str(old)[:80],
                    str(value)[:80],
                )
            base[key] = value

        return base

    def _safe_merge_soc(self, base: dict, llm_raw: dict, log: logging.Logger) -> dict:
        """Merge seguro para SOC - valida e filtra LLM output."""
        for key, value in llm_raw.items():
            if key not in _SOC_LLM_ALLOWED_KEYS:
                log.warning("LLM SOC: rejected key '%s' — not in allowed set.", key)
                continue

            # Validar containment_steps e investigation_queries: não sugerir bloquear IPs privados
            if key in ("containment_steps", "investigation_queries") and isinstance(
                value, list
            ):
                cleaned = []
                for step in value:
                    if not isinstance(step, str):
                        continue
                    # Detetar IPs privados
                    cidr_ips = re.findall(
                        r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b", step
                    )
                    private_cidrs = [
                        c for c in cidr_ips if _is_private_ip(c.split("/")[0])
                    ]
                    if private_cidrs:
                        log.warning(
                            "LLM SOC: '%s' item references private IP range(s) %s — dropped.",
                            key,
                            private_cidrs,
                        )
                        continue
                    cleaned.append(step)
                if cleaned:
                    base[key] = cleaned
                else:
                    log.warning(
                        "LLM SOC: all '%s' items were dropped — field not updated.", key
                    )
                continue

            old = base.get(key)
            if old != value:
                log.info(
                    "LLM SOC: merging '%s' (was %r → now %r).",
                    key,
                    str(old)[:80],
                    str(value)[:80],
                )
            base[key] = value

        return base

    def _build_ciso_prompt_with_cot(self, context: dict) -> str:
        """Build CISO prompt with Chain-of-Thought if enabled."""
        base_prompt = self._build_ciso_prompt_base(context)

        if LLM_COT_ENABLED:
            cot = self._cot.generate_ciso_cot(context)
            return f"{cot}\n\nNow produce the JSON output based on your reasoning above.\n\n{base_prompt}"

        return base_prompt

    def _build_ciso_prompt_base(self, context: dict) -> str:
        analyst_label = context.get("analyst_label", "Unknown")
        analyst_prob_s = context.get("analyst_prob_s", "?")
        top_tier = context.get("top_tier", "—")
        kc_phases_s = context.get("kc_phases_s", "unknown")
        n_alerts = context.get("n_alerts", 0)
        n_assets = context.get("n_assets", 0)
        n_iocs = context.get("n_iocs", 0)
        ioc_ipv4 = context.get("ioc_ipv4", [])
        ioc_fqdns = context.get("ioc_fqdns", [])
        assets = context.get("assets", [])
        nis2 = context.get("nis2", "")
        gdpr = context.get("gdpr", "")

        return (
            f"You are a senior CISO advisor writing for a board audience. No jargon. No repetition.\n"
            f"ANALYST DECISION: '{analyst_label}' confirmed at {analyst_prob_s} confidence. Risk: {top_tier}.\n"
            f"FACTS: {n_alerts} alerts, {n_assets} affected assets, {n_iocs} external IoCs.\n"
            f"Kill chain (chronological): {kc_phases_s}.\n"
            f"External IoCs: IPs={ioc_ipv4}, domains={ioc_fqdns}.\n"
            f"Affected assets: {assets[:5]}.\n"
            f"Regulatory context: NIS2={nis2[:80]}, GDPR={gdpr[:80]}.\n\n"
            "FIELD FUNCTIONS — each field has a DISTINCT purpose. Do NOT repeat information across fields:\n"
            "  why_it_matters   → 1 sentence: why executives should care (business risk, NOT technical)\n"
            "  what_was_detected → 1 sentence: purely factual — what behaviors were observed (NOT risk opinion)\n"
            "  analyst_assessment → 1 fluent paragraph: narrative synthesis connecting detection -> risk -> decision needed\n"
            "  immediate_actions → 3-5 actions, each with an owner team. Format: 'Action — Owner Team'\n"
            "  key_message      → 1 sentence: the executive decision required right now\n\n"
            "STRICT RULES:\n"
            "  - Do NOT declare breach or data stolen unless confirmed.\n"
            "  - Each immediate_action MUST include an owner.\n"
            "  - analyst_assessment must read like a human analyst wrote it — fluid prose, no bullet points.\n"
            "Return ONLY valid JSON (no markdown):\n"
            '{"why_it_matters":"<1 sentence: business risk>", '
            '"what_was_detected":"<1 sentence: factual observation>", '
            '"analyst_assessment":"<1 fluent paragraph>", '
            '"business_criticality":{"affected_services":"<e.g. Identity, File Services>","operational_risk":"<e.g. High probability of service interruption within 24h>","blast_radius":"<e.g. N endpoints across M segments>"}, '
            '"immediate_actions":["<action — Owner>","<action — Owner>","<action — Owner>"], '
            '"key_message":"<1 sentence: executive decision required>"}'
        )

    def _build_soc_prompt_with_cot(self, context: dict) -> str:
        """Build SOC prompt with Chain-of-Thought if enabled."""
        base_prompt = self._build_soc_prompt_base(context)

        if LLM_COT_ENABLED:
            cot = self._cot.generate_soc_cot(context)
            return f"{cot}\n\nNow produce the JSON output based on your reasoning above.\n\n{base_prompt}"

        return base_prompt

    def _build_soc_prompt_base(self, context: dict) -> str:
        analyst_label = context.get("analyst_label", "Unknown")
        top_tier = context.get("top_tier", "—")
        kc_phases_s = context.get("kc_phases_s", "unknown")
        ioc_ipv4 = context.get("ioc_ipv4", [])
        ioc_fqdns = context.get("ioc_fqdns", [])
        ioc_cves = context.get("ioc_cves", [])
        ioc_sample = context.get("ioc_sample", [])
        assets = context.get("assets", [])
        n_alerts = context.get("n_alerts", 0)

        return (
            f"You are a SOC L2 analyst. Be specific. Use real IOC values in queries.\n"
            f"VALIDATED INCIDENT: '{analyst_label}', tier={top_tier}.\n"
            f"KILL CHAIN (chronological): {kc_phases_s}.\n"
            f"Confirmed external IOCs: IPs={ioc_ipv4}, domains={ioc_fqdns}, CVEs={ioc_cves}.\n"
            f"Affected assets: {assets[:5]}. Total alerts: {n_alerts}.\n\n"
            "STRICT RULES:\n"
            "  - Do NOT suggest blocking private/internal IPs (10.x, 172.16-31.x, 192.168.x).\n"
            "  - investigation_queries MUST reference real IOC values from the facts above.\n"
            "  - priority_actions must be time-phased.\n\n"
            "Return ONLY valid JSON:\n"
            '{"threat_classification":"<specific type, max 12 words>", '
            '"priority_actions":{'
            '"immediate_0_1h":["<action1>","<action2>"],'
            '"short_term_1_4h":["<action1>","<action2>"],'
            '"sustained_4_24h":["<action1>","<action2>"]},'
            '"containment_steps":["<step1>","<step2>","<step3>"],'
            '"investigation_queries":["<query using real IOC values>","<query2>","<query3>"]}'
        )

    def _compute_context_hash(
        self, ciso_data: dict, soc_data: dict, report: dict
    ) -> str:
        """Compute hash for cache key."""
        import hashlib

        key_parts = [
            str(ciso_data.get("top_risk_tier", "")),
            str(soc_data.get("kill_chain_phases", [])),
            str(len(soc_data.get("iocs", []))),
            str(len(soc_data.get("detected_cves", []))),
            str(report.get("selected_hypothesis", {}).get("label", "")),
        ]
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]

    def _cross_validate(
        self, ciso_data: dict, soc_data: dict, report: dict
    ) -> Tuple[dict, dict]:
        """Cross-validate CISO and SOC reports for consistency."""
        log = logging.getLogger("agent2")

        # Verificar consistência entre classificações
        ciso_tier = ciso_data.get("top_risk_tier", "—")
        soc_phases = soc_data.get("kill_chain_phases", [])

        # Mapeamento esperado: certos tiers devem ter certas fases
        expected_phases_for_tier = {
            "CRITICAL": ["IMPACT", "EXFILTRATION"],
            "HIGH": ["LATERAL_MOVEMENT", "EXECUTION"],
            "MEDIUM-HIGH": ["INITIAL_ACCESS", "EXECUTION"],
            "MEDIUM": ["INITIAL_ACCESS"],
            "LOW": ["RECON"],
        }

        expected = expected_phases_for_tier.get(ciso_tier, [])
        missing = [p for p in expected if p not in soc_phases]

        if missing and LLM_CROSS_VALIDATION:
            log.warning(
                f"[CrossValidation] CISO tier {ciso_tier} missing phases {missing} in SOC report"
            )
            # Adicionar nota de consistência
            if "notes" not in ciso_data:
                ciso_data["notes"] = {}
            ciso_data["notes"][
                "cross_validation"
            ] = f"Missing expected phases: {missing}"

        return ciso_data, soc_data

    def enhance(
        self, ciso_data: dict, soc_data: dict, report: dict
    ) -> Tuple[dict, dict]:
        """Enriquece os relatórios CISO e SOC com LLM (com todas as melhorias)."""
        llm_success = False
        if not self.can_enhance():
            if isinstance(report, dict):
                metadata = report.setdefault("metadata", {})
                metadata["model_used"] = self.get_last_model_used()
                metadata["llm_provider"] = self.provider
                metadata["llm_used"] = llm_success

            return ciso_data, soc_data

        log = logging.getLogger("agent2")
        log.info(
            "Enhancing reports with LLM (enhanced mode with cache, COT, metrics)..."
        )

        start_time = time.time()

        try:
            # Extrair contexto para o prompt
            selected_hyp = report.get("selected_hypothesis", {})
            analyst_label = (
                selected_hyp.get("label", "Unknown")
                if isinstance(selected_hyp, dict)
                else str(selected_hyp)
            )
            analyst_prob = (
                selected_hyp.get("probability", 0.0)
                if isinstance(selected_hyp, dict)
                else 0.0
            )
            analyst_prob_s = f"{analyst_prob * 100:.0f}%" if analyst_prob else "?"

            top_tier = ciso_data.get("top_risk_tier", "—")
            categories = ciso_data.get("top_categories", [])
            nis2 = ciso_data.get("regulatory_impact", {}).get("nis2", "")
            gdpr = ciso_data.get("regulatory_impact", {}).get("gdpr", "")
            attack_pattern = ciso_data.get("attack_pattern", top_tier)
            incident_status = ciso_data.get("incident_status", "")
            kc_desc = ciso_data.get("kill_chain_description", "")
            cat_labels = (
                ", ".join(f"{n}({c})" for n, c in categories[:3])
                if categories
                else "none"
            )

            ioc_bundle = soc_data.get("ioc_bundle", {})
            n_iocs = len(soc_data.get("iocs", []))
            n_assets = len(soc_data.get("affected_assets", []))
            n_cves = len(soc_data.get("detected_cves", []))
            ioc_ipv4 = ioc_bundle.get("ipv4_addresses", [])[:5]
            ioc_fqdns = ioc_bundle.get("fqdns", [])[:5]
            ioc_cves = ioc_bundle.get("cve_ids", [])[:5]
            ioc_sample = soc_data.get("iocs", [])[:3]
            cve_sample = soc_data.get("detected_cves", [])[:3]
            kc_phases = soc_data.get("kill_chain_phases", [])
            kc_phases_s = ", ".join(kc_phases[:6]) or "unknown"
            n_alerts = soc_data.get("total_alerts", 0)
            n_triggers = soc_data.get("total_triggers", 0)
            assets = soc_data.get("affected_assets", [])

            # Calcular complexidade para seleção dinâmica de modelo
            complexity = self._complexity.calculate(
                phases=kc_phases,
                iocs=ioc_sample,
                cves=cve_sample,
                alert_count=n_alerts,
                phase_score=ciso_data.get("phase_score", 0),
            )
            log.info(f"[LLM] Incident complexity: {complexity:.2f}")

            # Construir contexto completo para hash e COT
            context = {
                "analyst_label": analyst_label,
                "analyst_prob_s": analyst_prob_s,
                "top_tier": top_tier,
                "attack_pattern": attack_pattern,
                "incident_status": incident_status,
                "kc_desc": kc_desc,
                "kc_phases_s": kc_phases_s,
                "cat_labels": cat_labels,
                "n_iocs": n_iocs,
                "n_assets": n_assets,
                "n_cves": n_cves,
                "nis2": nis2,
                "gdpr": gdpr,
                "ioc_ipv4": ioc_ipv4,
                "ioc_fqdns": ioc_fqdns,
                "ioc_cves": ioc_cves,
                "ioc_sample": ioc_sample,
                "cve_sample": cve_sample,
                "n_alerts": n_alerts,
                "n_triggers": n_triggers,
                "phases": kc_phases,
                "assets": assets,
                "iocs": ioc_sample,
                "cves": cve_sample,
            }

            # Computar hash para cache
            context_hash = (
                self._compute_context_hash(ciso_data, soc_data, report)
                if self._cache
                else ""
            )

            # CISO Prompt (com COT se ativado)
            ciso_prompt = self._build_ciso_prompt_with_cot(context)

            # SOC Prompt (com COT se ativado)
            soc_prompt = self._build_soc_prompt_with_cot(context)

            # Chamadas LLM
            ciso_start = time.time()
            ciso_llm_raw = self._call_llm(
                ciso_prompt, 600, context_hash + "_ciso", complexity
            )
            ciso_latency = (time.time() - ciso_start) * 1000

            soc_start = time.time()
            soc_llm_raw = self._call_llm(
                soc_prompt, 900, context_hash + "_soc", complexity
            )
            soc_latency = (time.time() - soc_start) * 1000

            # Processar respostas
            if ciso_llm_raw:
                ciso_llm_raw = re.sub(r"```(?:json)?|```", "", ciso_llm_raw).strip()
                try:
                    parsed = json.loads(ciso_llm_raw)
                    ciso_data = self._safe_merge_ciso(ciso_data, parsed, log)
                    llm_success = True

                    # Registrar métricas
                    if self._metrics:
                        metrics = self._metrics.evaluate_ciso_response(
                            parsed, {"latency_ms": ciso_latency}
                        )
                        log.info(
                            f"[LLM Quality] CISO score: {metrics['scores']['total']}/100, acceptable: {metrics['acceptable']}"
                        )

                except json.JSONDecodeError:
                    log.warning(
                        "LLM CISO: could not parse response as JSON — skipping enhancement."
                    )

            if soc_llm_raw:
                soc_llm_raw = soc_llm_raw.strip()
                soc_llm_raw = re.sub(r"```(?:json)?\s*", "", soc_llm_raw)
                soc_llm_raw = re.sub(r"```\s*$", "", soc_llm_raw)
                fb = soc_llm_raw.find("{")
                lb = soc_llm_raw.rfind("}")
                if fb != -1 and lb != -1:
                    soc_llm_raw = soc_llm_raw[fb : lb + 1]
                try:
                    parsed = json.loads(soc_llm_raw)
                    soc_data = self._safe_merge_soc(soc_data, parsed, log)
                    llm_success = True

                    # Registrar métricas
                    if self._metrics:
                        metrics = self._metrics.evaluate_soc_response(
                            parsed, {"latency_ms": soc_latency}
                        )
                        log.info(
                            f"[LLM Quality] SOC score: {metrics['scores']['total']}/100, acceptable: {metrics['acceptable']}"
                        )

                except json.JSONDecodeError as e:
                    log.warning("LLM SOC: could not parse JSON: %s", e)

            # Validação cruzada (se ativada)
            if LLM_CROSS_VALIDATION:
                ciso_data, soc_data = self._cross_validate(ciso_data, soc_data, report)

        except Exception as e:
            log.warning(f"LLM enhancement failed: {e}")

        total_latency = (time.time() - start_time) * 1000
        log.info(f"[LLM] Total enhancement completed in {total_latency:.0f}ms")

        return ciso_data, soc_data


# ============================================================================
# CVE Repository and MITRE Mapper
# ============================================================================


class CVERepository:
    """CVE analysis via NVD API"""

    @staticmethod
    def get_cve_details(cve_id: str) -> Optional[Dict]:
        """Fetch CVE details from NVD API"""
        import urllib.request
        import json

        try:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read())
                vulns = data.get("vulnerabilities", [])
                if vulns:
                    cve_data = vulns[0].get("cve", {})
                    metrics = cve_data.get("metrics", {})
                    cvss_v3 = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})

                    return {
                        "id": cve_id,
                        "description": cve_data.get("descriptions", [{}])[0].get(
                            "value", ""
                        ),
                        "cvss_score": cvss_v3.get("baseScore", "N/A"),
                        "severity": cvss_v3.get("baseSeverity", "UNKNOWN"),
                        "attack_vector": cvss_v3.get("attackVector", "UNKNOWN"),
                        "exploitability_score": metrics.get("cvssMetricV31", [{}])[
                            0
                        ].get("exploitabilityScore", "N/A"),
                        "impact_score": metrics.get("cvssMetricV31", [{}])[0].get(
                            "impactScore", "N/A"
                        ),
                    }
            return None
        except Exception as e:
            _log.error(f"[Agent2] Failed to fetch CVE {cve_id}: {e}")
            return None


class MITREMapper:
    """MITRE ATT&CK mapping"""

    # Pre-computed MITRE technique mappings (from report)
    TECHNIQUE_MAP = {
        "T1486": {
            "name": "Data Encrypted for Impact",
            "tactic": "Impact",
            "phase": "IMPACT",
        },
        "T1485": {"name": "Data Destruction", "tactic": "Impact", "phase": "IMPACT"},
        "T1041": {
            "name": "Exfiltration Over C2 Channel",
            "tactic": "Exfiltration",
            "phase": "EXFILTRATION",
        },
        "T1110": {
            "name": "Brute Force",
            "tactic": "Credential Access",
            "phase": "INITIAL_ACCESS",
        },
        "T1059": {
            "name": "Command and Scripting Interpreter",
            "tactic": "Execution",
            "phase": "EXECUTION",
        },
        "T1195": {
            "name": "Supply Chain Compromise",
            "tactic": "Initial Access",
            "phase": "INITIAL_ACCESS",
        },
        "T1498": {
            "name": "Network Denial of Service",
            "tactic": "Impact",
            "phase": "IMPACT",
        },
        "T1566": {
            "name": "Phishing",
            "tactic": "Initial Access",
            "phase": "INITIAL_ACCESS",
        },
        "T1190": {
            "name": "Exploit Public-Facing Application",
            "tactic": "Initial Access",
            "phase": "INITIAL_ACCESS",
        },
        "T1078": {
            "name": "Valid Accounts",
            "tactic": "Defense Evasion",
            "phase": "PERSISTENCE",
        },
        "T1496": {
            "name": "Resource Hijacking",
            "tactic": "Impact",
            "phase": "EXECUTION",
        },
        "T1071": {
            "name": "Application Layer Protocol",
            "tactic": "Command and Control",
            "phase": "EXECUTION",
        },
        "T1595": {
            "name": "Active Scanning",
            "tactic": "Reconnaissance",
            "phase": "RECON",
        },
    }

    @staticmethod
    def get_techniques_for_phases(phases: List[str]) -> List[Dict]:
        """Get MITRE techniques relevant to detected phases"""
        techniques = []
        for phase in phases:
            for tech_id, info in MITREMapper.TECHNIQUE_MAP.items():
                if info.get("phase") == phase:
                    techniques.append(
                        {
                            "id": tech_id,
                            "name": info["name"],
                            "tactic": info["tactic"],
                            "phase": phase,
                        }
                    )
        return techniques[:10]  # Limit to top 10


# ============================================================================
# Incident Analyzer (LLM-based 360° analysis)
# ============================================================================


class IncidentAnalyzer:
    """LLM-based incident analyzer for 360° reports"""

    @staticmethod
    def analyze_incident(
        incident_id: str,
        label: str,
        score: float,
        tier: str,
        method: str,
        alerts: List[Dict],
    ) -> Dict:
        """
        Enriquece o incidente com inteligência cognitiva e traduz rótulos genéricos para ameaças reais.
        """
        # ─── CLASSIFICAÇÃO COGNITIVA DINÂMICA (RANSOMWARE / EXFILTRATION) ───
        categories = [
            str(a.get("Category", a.get("category", ""))).lower() for a in alerts
        ]
        phases = [str(a.get("Kill Chain", a.get("phase", ""))).lower() for a in alerts]

        dynamic_label = label
        # Se detetar assinaturas de impacto, encriptação ou destruição, assume Ransomware nos Badges
        if "impact" in categories or "encryption" in categories or "impact" in phases:
            dynamic_label = "Ransomware Activity Campaign"
        elif "exfiltration" in categories or "exfil" in categories:
            dynamic_label = "Advanced Data Exfiltration Campaign"
        elif label == "Major Breach with Impact":
            dynamic_label = "Ransomware & Exfiltration Attack"

        raw_text = ""
        if LLM_AVAILABLE:
            try:
                raw_text = IncidentAnalyzer.analyze_window(alerts, dynamic_label, tier)
            except Exception:
                raw_text = f"Análise automatizada de segurança. Sequência de eventos condizente com {dynamic_label}."
        else:
            raw_text = f"Análise automatizada de segurança. Sequência de eventos condizente com {dynamic_label}."

        parts = raw_text.split("\n\n")
        exec_summary = (
            parts[0].strip()
            if parts
            else f"Atividade detetada e catalogada operacionalmente como {dynamic_label}."
        )
        tactical_an = raw_text if len(parts) <= 1 else "\n".join(parts[1:]).strip()

        from agent2.analyzers import DataExtractor

        assets_extracted = DataExtractor.extract_assets(alerts)
        cves_extracted = DataExtractor.extract_cves(alerts)

        risk_tier = tier if tier and tier != "—" else "HIGH"

        return {
            "incident_id": str(incident_id),
            "label": str(
                dynamic_label
            ),  # ─── ATUALIZA OS BADGES DO DASHBOARD DINAMICAMENTE
            "score": float(score),
            "tier": str(risk_tier),
            "method": str(method),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "executive_summary": exec_summary
            if exec_summary
            else f"Análise para {dynamic_label}.",
            "tactical_analysis": tactical_an if tactical_an else raw_text,
            "mitre_matrix": {
                "tactics": [alert.get("Kill Chain", "EXECUTION") for alert in alerts],
                "techniques": [alert.get("MitreAttack", "—") for alert in alerts],
            },
            "affected_assets": [{"asset": a, "type": "Host"} for a in assets_extracted]
            if assets_extracted
            else [{"asset": "dc-ad01.corp.local", "type": "Host"}],
            "detected_cves": [
                {"cve_id": c, "severity": "HIGH"} for c in cves_extracted
            ],
            "total_alerts": len(alerts),
        }

    @staticmethod
    def _get_english_fallback(pattern: str, assets: list) -> Dict[str, Any]:
        """Fallback de segurança estruturado 100% em inglês."""
        return {
            "business_impact": f"Critical threat pattern '{pattern}' detected. Potential operational downtime and compliance risk affecting assets: {', '.join(assets) if assets else 'internal network'}.",
            "threat_classification": "Unclassified Advanced Cyber Security Incident",
            "containment_steps": [
                "Isolate all affected or communicating endpoints from the corporate network.",
                "Revoke active session tokens and domain credentials related to the assets.",
            ],
            "investigation_queries": [
                "// Fallback Generic Hunting Query\\nDeviceProcessEvents | where DeviceName in~ ("
                + ",".join([f"'{a}'" for a in assets])
                + ")"
                if assets
                else "// No assets specified"
            ],
            "soc_recommendations": [
                "Deploy aggressive Endpoint Detection and Response (EDR) scanning on the affected segment.",
                "Inspect egress firewall traffic logs for large outbound transfers.",
            ],
            "strategic_recommendations": [
                "Review privileged access management controls and enforce strict Zero-Trust isolation.",
                "Initiate full forensic engagement to map the threat actor's initial entry vector.",
            ],
        }


# ============================================================================
# CVE Report Generator (LLM-based)
# ============================================================================


class CVEReportGenerator:
    """Generate CVE analysis reports using LLM"""

    @staticmethod
    def analyze_cve(cve_id: str) -> Optional[Dict]:
        """Analyze a CVE using NVD data and LLM"""

        # Fetch CVE details from NVD
        cve_data = CVERepository.get_cve_details(cve_id)
        if not cve_data:
            return None

        if not LLM_AVAILABLE:
            return CVEReportGenerator._fallback_cve_analysis(cve_data)

        prompt = f"""Analyze this CVE vulnerability for a SOC/CISO audience:

CVE ID: {cve_data['id']}
Description: {cve_data['description']}
CVSS Score: {cve_data['cvss_score']} ({cve_data['severity']})
Attack Vector: {cve_data['attack_vector']}

Provide:
1. Executive summary (2 sentences)
2. Business impact assessment
3. Recommended remediation steps
4. MITRE ATT&CK mapping suggestion

Return JSON only:
{{
"executive_summary": "string",
"business_impact": "string",
"remediation_steps": ["step1", "step2", "step3"],
"suspected_mitre_technique": "TXXXX",
"priority": "CRITICAL|HIGH|MEDIUM|LOW"
}}"""

        response = _call_llm(prompt, max_tokens=min(AGENT2_MAX_TOKENS, 800))

        if response:
            try:
                response = re.sub(r"```json\s*|```\s*", "", response.strip())
                result = json.loads(response)
                result.update(cve_data)
                return result
            except json.JSONDecodeError:
                return CVEReportGenerator._fallback_cve_analysis(cve_data)

        return CVEReportGenerator._fallback_cve_analysis(cve_data)

    @staticmethod
    def _fallback_cve_analysis(cve_data: Dict) -> Dict:
        """Fallback CVE analysis without LLM"""
        severity = cve_data.get("severity", "UNKNOWN")
        priority = (
            "CRITICAL"
            if severity == "CRITICAL"
            else "HIGH"
            if severity in ["HIGH", "MEDIUM"]
            else "MEDIUM"
        )

        return {
            **cve_data,
            "executive_summary": f"CVE {cve_data['id']} has CVSS score {cve_data['cvss_score']} ({severity}). "
            f"Attack vector: {cve_data['attack_vector']}.",
            "business_impact": "Evaluate affected systems and apply patches according to change management",
            "remediation_steps": [
                "Verify if systems are affected",
                "Apply vendor patch or workaround",
                "Monitor for exploitation attempts",
                "Document in vulnerability register",
            ],
            "priority": priority,
        }
