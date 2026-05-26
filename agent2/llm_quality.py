"""
LLM Quality Metrics - Monitorização da qualidade das respostas do LLM
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

import sys
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

from core.logging import get_logger
from shared_config import LLM_CACHE_DIR, LLM_CACHE_TTL_SECONDS, LLM_QUALITY_METRICS_ENABLED

_logger = get_logger("agent2.llm_quality")

# ============================================================================
# Cache Manager
# ============================================================================

class LLMCache:
  """Cache para respostas LLM baseado em hash das entradas."""
  
  def __init__(self, ttl_seconds: int = LLM_CACHE_TTL_SECONDS):
    self._cache: Dict[str, Dict] = {}
    self._ttl = ttl_seconds
    self._cache_file = LLM_CACHE_DIR / "llm_cache.json"
    self._load()
  
  def _compute_key(self, prompt: str, context: str = "") -> str:
    """Computa hash da entrada para usar como chave de cache."""
    content = f"{prompt}|{context}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]
  
  def get(self, prompt: str, context: str = "") -> Optional[str]:
    """Retorna resposta em cache se existir e não expirada."""
    key = self._compute_key(prompt, context)
    entry = self._cache.get(key)
    
    if entry is None:
      return None
    
    # Verifica expiração
    if time.time() - entry.get("cached_at", 0) > self._ttl:
      del self._cache[key]
      return None
    
    _logger.debug(f"[LLMCache] Hit for key {key[:8]}...")
    return entry.get("response")
  
  def set(self, prompt: str, response: str, context: str = "") -> None:
    """Armazena resposta em cache."""
    key = self._compute_key(prompt, context)
    self._cache[key] = {
      "response": response,
      "cached_at": time.time(),
      "prompt_hash": key,
    }
    _logger.debug(f"[LLMCache] Stored for key {key[:8]}...")
    self._save()
  
  def _load(self) -> None:
    """Carrega cache do disco."""
    if self._cache_file.exists():
      try:
        data = json.loads(self._cache_file.read_text(encoding="utf-8"))
        # Filtrar entradas expiradas
        now = time.time()
        for key, entry in data.items():
          if now - entry.get("cached_at", 0) <= self._ttl:
            self._cache[key] = entry
        _logger.info(f"[LLMCache] Loaded {len(self._cache)} entries from disk")
      except Exception as e:
        _logger.warning(f"[LLMCache] Failed to load cache: {e}")
  
  def _save(self) -> None:
    """Persiste cache em disco."""
    try:
      LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
      self._cache_file.write_text(
        json.dumps(self._cache, indent=2, default=str),
        encoding="utf-8"
      )
    except Exception as e:
      _logger.warning(f"[LLMCache] Failed to save cache: {e}")
  
  def clear(self) -> None:
    """Limpa toda a cache."""
    self._cache.clear()
    self._save()
    _logger.info("[LLMCache] Cache cleared")
  
  def stats(self) -> Dict:
    """Retorna estatísticas da cache."""
    return {
      "size": len(self._cache),
      "ttl_seconds": self._ttl,
      "cache_file": str(self._cache_file),
    }

# ============================================================================
# Quality Metrics
# ============================================================================

class LLMQualityMetrics:
  """Métricas de qualidade para respostas LLM."""
  
  # Padrões de linguagem de breach não confirmada
  _BREACH_PATTERNS = re.compile(
    r"\b(breach(ed)?|compromised our|exfiltrat(ed|ion)|confirmed data loss|"
    r"data stolen|systems? taken over|fully compromised|we have been hacked|"
    r"attackers successfully|intruders gained|backdoor installed)\b",
    re.IGNORECASE,
  )
  
  # Padrões de IPs privados (não devem ser sugeridos para bloqueio)
  _PRIVATE_IP_PATTERN = re.compile(
    r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"127\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"169\.254\.\d{1,3}\.\d{1,3})\b"
  )
  
  def __init__(self):
    self._metrics_file = LLM_CACHE_DIR / "quality_metrics.json"
    self._metrics: List[Dict] = []
    self._load()
  
  def _load(self) -> None:
    """Carrega métricas históricas."""
    if self._metrics_file.exists():
      try:
        self._metrics = json.loads(self._metrics_file.read_text(encoding="utf-8"))
        _logger.info(f"[LLMQuality] Loaded {len(self._metrics)} metric entries")
      except Exception as e:
        _logger.warning(f"[LLMQuality] Failed to load metrics: {e}")
  
  def _save(self) -> None:
    """Persiste métricas."""
    try:
      # Manter apenas últimas 1000 entradas
      if len(self._metrics) > 1000:
        self._metrics = self._metrics[-1000:]
      self._metrics_file.write_text(
        json.dumps(self._metrics, indent=2, default=str),
        encoding="utf-8"
      )
    except Exception as e:
      _logger.warning(f"[LLMQuality] Failed to save metrics: {e}")
  
  def _check_ownership(self, text: str) -> bool:
    """Verifica se uma ação tem ownership (responsável)."""
    owners = re.compile(
      r"(IR team|CERT|CISO|SOC|Legal|Board|Counsel|"
      r"Incident Commander|Security Team|Management|L[0-9] analyst|"
      r"Equipa de Segurança|Analista|Administrador|Engenheiro|"
      r"DevOps|Rede|Sistemas|Forensics|Threat Hunting)",
      re.IGNORECASE,
    )
    return bool(owners.search(text))
  
  def evaluate_ciso_response(self, response: dict, context: dict) -> Dict:
    """Avalia qualidade da resposta CISO."""
    metrics = {
      "timestamp": datetime.now(timezone.utc).isoformat(),
      "type": "ciso",
      "scores": {},
      "issues": [],
      "latency_ms": context.get("latency_ms", 0),
    }
    
    # 1. Verificar linguagem de breach não confirmada
    for field in ["why_it_matters", "what_was_detected", "key_message"]:
      text = response.get(field, "")
      if self._BREACH_PATTERNS.search(text):
        metrics["issues"].append({
          "field": field,
          "issue": "unconfirmed_breach_language",
          "snippet": text[:100]
        })
    
    # 2. Verificar ownership nas immediate_actions
    actions = response.get("immediate_actions", [])
    actions_with_owner = sum(1 for a in actions if self._check_ownership(a))
    if actions:
      ownership_rate = actions_with_owner / len(actions)
      metrics["scores"]["ownership_rate"] = round(ownership_rate, 2)
      if ownership_rate < 0.8:
        metrics["issues"].append({
          "field": "immediate_actions",
          "issue": f"low_ownership_rate ({ownership_rate:.0%})",
        })
    
    # 3. Verificar completude
    required_fields = ["why_it_matters", "what_was_detected", "key_message"]
    missing = [f for f in required_fields if not response.get(f)]
    if missing:
      metrics["issues"].append({
        "issue": "missing_fields",
        "fields": missing
      })
    metrics["scores"]["completeness"] = round(
      (len(required_fields) - len(missing)) / len(required_fields), 2
    )
    
    # 4. Score total (0-100)
    base_score = 100
    base_score -= len(metrics["issues"]) * 10
    base_score = max(0, min(100, base_score))
    metrics["scores"]["total"] = base_score
    
    # 5. Determinar se a resposta é aceitável
    metrics["acceptable"] = (
      metrics["scores"]["completeness"] >= 0.66 and
      metrics["scores"].get("ownership_rate", 1.0) >= 0.5 and
      len([i for i in metrics["issues"] if i.get("issue") == "unconfirmed_breach_language"]) == 0
    )
    
    self._metrics.append(metrics)
    self._save()
    
    return metrics
  
  def evaluate_soc_response(self, response: dict, context: dict) -> Dict:
    """Avalia qualidade da resposta SOC."""
    metrics = {
      "timestamp": datetime.now(timezone.utc).isoformat(),
      "type": "soc",
      "scores": {},
      "issues": [],
      "latency_ms": context.get("latency_ms", 0),
    }
    
    # 1. Verificar sugestão de bloqueio de IPs privados
    for field in ["containment_steps", "investigation_queries"]:
      steps = response.get(field, [])
      for step in steps:
        if self._PRIVATE_IP_PATTERN.search(step):
          metrics["issues"].append({
            "field": field,
            "issue": "private_ip_suggestion",
            "snippet": step[:100]
          })
    
    # 2. Verificar completude
    required_fields = ["threat_classification", "containment_steps", "investigation_queries"]
    for field in required_fields:
      value = response.get(field)
      if not value or (isinstance(value, list) and len(value) == 0):
        metrics["issues"].append({
          "field": field,
          "issue": "empty_or_missing"
        })
    
    metrics["scores"]["completeness"] = round(
      (len([f for f in required_fields if response.get(f)]) / len(required_fields)), 2
    )
    
    # 3. Score total
    base_score = 100
    base_score -= len(metrics["issues"]) * 15
    base_score = max(0, min(100, base_score))
    metrics["scores"]["total"] = base_score
    
    # 4. Aceitabilidade
    metrics["acceptable"] = metrics["scores"]["completeness"] >= 0.66
    
    self._metrics.append(metrics)
    self._save()
    
    return metrics
  
  def get_summary(self) -> Dict:
    """Retorna resumo das métricas."""
    if not self._metrics:
      return {"total_requests": 0, "avg_score": 0, "acceptance_rate": 0}
    
    total = len(self._metrics)
    avg_score = sum(m.get("scores", {}).get("total", 0) for m in self._metrics) / total
    acceptance_rate = sum(1 for m in self._metrics if m.get("acceptable", False)) / total
    
    # Contagem de issues por tipo
    issue_counts = defaultdict(int)
    for m in self._metrics:
      for issue in m.get("issues", []):
        issue_type = issue.get("issue", "unknown")
        issue_counts[issue_type] += 1
    
    return {
      "total_requests": total,
      "avg_score": round(avg_score, 1),
      "acceptance_rate": round(acceptance_rate * 100, 1),
      "issue_breakdown": dict(issue_counts),
      "by_type": {
        "ciso": len([m for m in self._metrics if m.get("type") == "ciso"]),
        "soc": len([m for m in self._metrics if m.get("type") == "soc"]),
      }
    }
  
  def get_recent_issues(self, limit: int = 20) -> List[Dict]:
    """Retorna issues recentes para análise."""
    issues = []
    for m in self._metrics[-limit:]:
      for issue in m.get("issues", []):
        issues.append({
          "timestamp": m.get("timestamp"),
          "type": m.get("type"),
          **issue
        })
    return issues

# ============================================================================
# Complexidade Calculator (para seleção dinâmica de modelo)
# ============================================================================

class ComplexityCalculator:
  """Calcula complexidade de um incidente para seleção dinâmica de modelo."""
  
  @staticmethod
  def calculate(phases: List[str], iocs: List[str], cves: List[str], 
         alert_count: int, phase_score: float) -> float:
    """Retorna score de complexidade entre 0 e 1."""
    score = 0.0
    
    # 1. Número de fases (0-0.3)
    phase_score_weight = min(0.3, len(phases) * 0.05)
    score += phase_score_weight
    
    # 2. Presença de IOCs (0-0.2)
    ioc_weight = min(0.2, len(iocs) * 0.02)
    score += ioc_weight
    
    # 3. Presença de CVEs (0-0.2)
    cve_weight = min(0.2, len(cves) * 0.05)
    score += cve_weight
    
    # 4. Número de alertas (0-0.15)
    alert_weight = min(0.15, alert_count / 50)
    score += alert_weight
    
    # 5. Phase score (0-0.15)
    phase_contrib = min(0.15, phase_score / 100)
    score += phase_contrib
    
    return min(1.0, score)
  
  @staticmethod
  def select_model(complexity: float) -> str:
    """Seleciona modelo baseado na complexidade."""
    if complexity >= 0.8:
      return "claude-3-opus"  # melhor qualidade
    elif complexity >= 0.5:
      return "claude-haiku"   # equilibrado
    else:
      return "llama3.2"       # rápido e barato

# ============================================================================
# Chain-of-Thought Generator
# ============================================================================

class ChainOfThoughtGenerator:
  """Gera prompts Chain-of-Thought para melhor rastreabilidade."""
  
  @staticmethod
  def generate_ciso_cot(context: dict) -> str:
    """Gera prompt COT para relatório CISO."""
    phases = context.get("phases", [])
    iocs = context.get("iocs", [])
    cves = context.get("cves", [])
    alert_count = context.get("alert_count", 0)
    top_tier = context.get("top_tier", "MEDIUM")
    
    return f"""
First, reason step by step:

STEP 1 - Phase Analysis:
- Detected kill chain phases: {phases}
- Progression: {' → '.join(phases) if phases else 'single phase'}
- {len(phases)} phases detected → severity level: {'HIGH' if len(phases) >= 3 else 'MEDIUM' if len(phases) >= 2 else 'LOW'}

STEP 2 - Evidence Assessment:
- Total alerts: {alert_count}
- External IOCs: {len(iocs)} ({', '.join(iocs[:3]) if iocs else 'none'})
- Known vulnerabilities (CVEs): {len(cves)} ({', '.join(cves[:3]) if cves else 'none'})
- Risk tier: {top_tier}

STEP 3 - Attack Pattern Identification:
- Looking for patterns: {'Ransomware' if 'IMPACT' in phases else ''}
- {'APT activity' if 'LATERAL_MOVEMENT' in phases and 'PERSISTENCE' in phases else ''}
- {'Credential compromise' if 'INITIAL_ACCESS' in phases and 'CREDENTIAL' in str(context) else ''}

STEP 4 - Business Impact Assessment:
- Potential operational disruption: {'HIGH' if 'IMPACT' in phases else 'MEDIUM'}
- Data exposure risk: {'HIGH' if 'EXFILTRATION' in phases else 'LOW'}
- Regulatory implications: {'NIS2 notification likely' if top_tier in ['CRITICAL', 'HIGH'] else 'Monitor only'}

STEP 5 - Recommended Actions (with owners):
1. [Action] — [Owner Team]
2. [Action] — [Owner Team]
3. [Action] — [Owner Team]

Now, based on this reasoning, produce the JSON output.
"""
  
  @staticmethod
  def generate_soc_cot(context: dict) -> str:
    """Gera prompt COT para relatório SOC."""
    phases = context.get("phases", [])
    iocs = context.get("iocs", [])
    cves = context.get("cves", [])
    assets = context.get("assets", [])
    
    return f"""
First, reason step by step:

STEP 1 - Kill Chain Reconstruction (chronological):
{chr(10).join([f'- Phase {i+1}: {p}' for i, p in enumerate(phases)])}

STEP 2 - IOC Analysis:
- Suspicious IPs: {len([i for i in iocs if re.match(r'\\d+\\.\\d+\\.\\d+\\.\\d+', i)])}
- Malicious domains: {len([i for i in iocs if '.' in i and not re.match(r'\\d+\\.\\d+\\.\\d+\\.\\d+', i)])}
- Critical IOCs requiring immediate action: {', '.join(iocs[:3]) if iocs else 'none'}

STEP 3 - Vulnerability Assessment (CVEs):
- Total CVEs: {len(cves)}
- Prioritize patching: {', '.join(cves[:3]) if cves else 'none'}

STEP 4 - Affected Assets:
- Assets identified: {len(assets)}
- Prioritize investigation: {', '.join(assets[:3]) if assets else 'none'}

STEP 5 - Containment Strategy:
- Phase-based containment:
 * RECON: Block scanning IPs at perimeter
 * INITIAL_ACCESS: Reset credentials, block indicators
 * EXECUTION: Isolate hosts, kill processes
 * LATERAL_MOVEMENT: Segment network, audit accounts
 * EXFILTRATION: Block C2, preserve logs
 * IMPACT: Activate backups, restore from clean

STEP 6 - Investigation Queries (SIEM/EDR):
- Query 1: Search for IOCs across all hosts
- Query 2: Timeline reconstruction for affected assets
- Query 3: Lateral movement patterns

Now, based on this reasoning, produce the JSON output.
"""

# Singleton instances
_llm_cache: Optional[LLMCache] = None
_quality_metrics: Optional[LLMQualityMetrics] = None
_complexity_calculator: Optional[ComplexityCalculator] = None
_cot_generator: Optional[ChainOfThoughtGenerator] = None

def get_llm_cache() -> LLMCache:
  global _llm_cache
  if _llm_cache is None:
    _llm_cache = LLMCache()
  return _llm_cache

def get_quality_metrics() -> LLMQualityMetrics:
  global _quality_metrics
  if _quality_metrics is None:
    _quality_metrics = LLMQualityMetrics()
  return _quality_metrics

def get_complexity_calculator() -> ComplexityCalculator:
  global _complexity_calculator
  if _complexity_calculator is None:
    _complexity_calculator = ComplexityCalculator()
  return _complexity_calculator

def get_cot_generator() -> ChainOfThoughtGenerator:
  global _cot_generator
  if _cot_generator is None:
    _cot_generator = ChainOfThoughtGenerator()
  return _cot_generator
