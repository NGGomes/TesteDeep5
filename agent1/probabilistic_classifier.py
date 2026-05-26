"""
Classificador Probabilístico Online — ENISA sequence → CISO options.

Implementa um classificador Naive Bayes online que:
 1. Usa as probabilidades estáticas de SEQUENCE_TO_CISO como prior.
 2. Actualiza as probabilidades com base nos outcomes confirmados pelo operador
  (loop de aprendizagem — retroalimentação).
 3. Persiste os parâmetros aprendidos em disco para sobreviver a reinicios.

Design:
 - Estrutura de dados principal: tabela de contagens
   _counts[phase_key][ciso_label] = {"confirmed": int, "rejected": int}
  onde phase_key é uma string canónica da sequência de fases, ex. "RECON|INITIAL_ACCESS".
 - As probabilidades são recalculadas a partir das contagens com suavização de Laplace.
 - O prior (SEQUENCE_TO_CISO) é mixado com as contagens aprendidas via peso configurável.
"""

from __future__ import annotations

import json
import math
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from core.logging import get_logger
from agent1.mappings import get_ciso_id_by_name

_logger = get_logger("agent1.probabilistic_classifier")

import sys
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(_PROJECT_ROOT))

from shared_config import AGENT1_REPORTS_DIR, PROBABILISTIC_MAX_HYPOTHESES

# ── Ficheiro de persistência ───────────────────────────────────────────────────
_CLASSIFIER_FILE = AGENT1_REPORTS_DIR / "classifier_state.json"

# Peso do prior estático vs contagens aprendidas.
# 0.0 = só prior estático (comportamento original)
# 1.0 = só contagens aprendidas
# 0.3 = 30% aprendizagem, 70% prior (recomendado para início)
_LEARNING_WEIGHT = 0.3

# Suavização de Laplace — evita probabilidade zero para categorias não vistas
_LAPLACE_ALPHA = 1.0

class ProbabilisticClassifier:
  """
  Classificador online que mapeia sequências de fases ENISA em opções CISO
  com probabilidades actualizadas por feedback do operador.
  """

  def __init__(self) -> None:
    self._lock = threading.RLock()

    # counts[phase_key][ciso_label] = {"confirmed": int, "rejected": int, "total": int}
    self._counts: Dict[str, Dict[str, Dict[str, int]]] = {}

    # Histórico de predições para auditoria
    self._prediction_log: List[Dict] = []

    # Total de confirmações recebidas
    self._total_confirmations: int = 0

    self._load()

  # ── Persistência ──────────────────────────────────────────────────────────

  def _load(self) -> None:
    if _CLASSIFIER_FILE.exists():
      try:
        data = json.loads(_CLASSIFIER_FILE.read_text(encoding="utf-8"))
        self._counts = data.get("counts", {})
        self._total_confirmations = data.get("total_confirmations", 0)
        self._prediction_log = data.get("prediction_log", [])[-200:]
        _logger.info(
          f"[Classifier] Loaded: {len(self._counts)} phase-keys, "
          f"{self._total_confirmations} confirmations"
        )
      except Exception as e:
        _logger.warning(f"[Classifier] Could not load state: {e}")

  def _save(self) -> None:
    try:
      _CLASSIFIER_FILE.parent.mkdir(parents=True, exist_ok=True)
      _CLASSIFIER_FILE.write_text(
        json.dumps({
          "counts": self._counts,
          "total_confirmations": self._total_confirmations,
          "prediction_log": self._prediction_log[-200:],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8"
      )
    except Exception as e:
      _logger.warning(f"[Classifier] Could not save state: {e}")

  # ── Chave canónica ────────────────────────────────────────────────────────

  @staticmethod
  def _phase_key(phases: List[str]) -> str:
    """Converte lista de fases em chave canónica para lookup."""
    return "|".join(phases) if phases else "UNKNOWN"

  # ── Predição ──────────────────────────────────────────────────────────────

  def predict(
    self,
    phases: List[str],
    prior_options: List[Tuple[str, float]],
) -> List[Tuple[str, int, float]]:  # ← mudar tipo de retorno
    """
    Retorna lista de (ciso_label, ciso_id, probability) ordenada por probabilidade
    decrescente, combinando o prior estático com as contagens aprendidas.
    """
    if not prior_options:
        result = []
        for label, prob in prior_options:
            ciso_id = get_ciso_id_by_name(label)
            result.append((label, ciso_id, prob))
        return result

    key = self._phase_key(phases)

    with self._lock:
        learned = self._counts.get(key, {})

    if not learned or self._total_confirmations == 0:
        # Sem dados aprendidos — devolve o prior inalterado com IDs
        result = []
        for label, prob in prior_options[:PROBABILISTIC_MAX_HYPOTHESES]:
            ciso_id = get_ciso_id_by_name(label)
            result.append((label, ciso_id, prob))
        return result

    # Conjunto de todas as categorias (prior + aprendidas)
    all_cats = {label for label, _ in prior_options} | set(learned.keys())

    # Probabilidades do prior indexadas
    prior_map: Dict[str, float] = {label: prob for label, prob in prior_options}

    # Probabilidade aprendida via Laplace smoothing
    total_confirmed = sum(v.get("confirmed", 0) for v in learned.values())
    n_cats = len(all_cats)

    learned_probs: Dict[str, float] = {}
    for cat in all_cats:
        count_confirmed = learned.get(cat, {}).get("confirmed", 0)
        learned_probs[cat] = (count_confirmed + _LAPLACE_ALPHA) / (
            total_confirmed + _LAPLACE_ALPHA * n_cats
        )

    # Normalizar prior
    prior_total = sum(prior_map.get(c, 1e-6) for c in all_cats)
    norm_prior: Dict[str, float] = {
        c: prior_map.get(c, 1e-6) / prior_total for c in all_cats
    }

    # Mistura: (1-w)*prior + w*learned
    w = _LEARNING_WEIGHT
    mixed: Dict[str, float] = {
        c: (1 - w) * norm_prior[c] + w * learned_probs.get(c, 0)
        for c in all_cats
    }

    # Normalizar mistura
    total_mixed = sum(mixed.values())
    
    # Ordenar por probabilidade decrescente
    sorted_items = sorted(
        [(c, mixed[c] / total_mixed) for c in all_cats],
        key=lambda x: -x[1]
    )

    # Adicionar os IDs ao resultado
    result = []
    for label, prob in sorted_items[:PROBABILISTIC_MAX_HYPOTHESES]:
        ciso_id = get_ciso_id_by_name(label)
        result.append((label, ciso_id, prob))
    
    return result

  
  # ── Aprendizagem — feedback do operador ───────────────────────────────────

  def record_confirmation(
    self,
    phases: List[str],
    confirmed_label: str,
    all_options: List[Tuple[str, float]],
  ) -> None:
    """
    Regista que o operador confirmou `confirmed_label` para a sequência
    de fases dada. Actualiza as contagens e persiste.

    Args:
      phases: sequência de fases da janela confirmada
      confirmed_label: categoria CISO escolhida pelo operador
      all_options: todas as opções que foram apresentadas
    """
    key = self._phase_key(phases)

    with self._lock:
      if key not in self._counts:
        self._counts[key] = {}

      # Incrementa confirmação
      if confirmed_label not in self._counts[key]:
        self._counts[key][confirmed_label] = {"confirmed": 0, "rejected": 0, "total": 0}
      self._counts[key][confirmed_label]["confirmed"] += 1
      self._counts[key][confirmed_label]["total"] += 1

      # Incrementa rejeição para as outras opções apresentadas
      for label, _ in all_options:
        if label != confirmed_label:
          if label not in self._counts[key]:
            self._counts[key][label] = {"confirmed": 0, "rejected": 0, "total": 0}
          self._counts[key][label]["rejected"] += 1
          self._counts[key][label]["total"] += 1

      self._total_confirmations += 1

      self._prediction_log.append({
        "phase_key": key,
        "confirmed": confirmed_label,
        "options": [l for l, _ in all_options],
        "total_confirmations": self._total_confirmations,
      })

      self._save()

    _logger.info(
      f"[Classifier] Confirmation recorded: key={key!r}, "
      f"confirmed={confirmed_label!r}, total={self._total_confirmations}"
    )

  def record_timeout_confirmation(
    self,
    phases: List[str],
    top_label: str,
    all_options: List[Tuple[str, float]],
  ) -> None:
    """
    Confirmação automática por timeout — conta como sinal fraco (peso 0.5).
    Usa a mesma lógica mas com contagem fraccionária arredondada.
    """
    # Para timeouts contamos como 0 confirmações explícitas
    # (não queremos que o modelo aprenda a confirmar por inércia)
    _logger.debug(
      f"[Classifier] Timeout auto-confirm ignored for learning: {top_label!r}"
    )

  # ── Estatísticas ──────────────────────────────────────────────────────────

  def get_stats(self) -> Dict:
    with self._lock:
      return {
        "total_confirmations": self._total_confirmations,
        "phase_keys_learned": len(self._counts),
        "learning_weight": _LEARNING_WEIGHT,
        "counts_summary": {
          k: {cat: v["confirmed"] for cat, v in cats.items() if v["confirmed"] > 0}
          for k, cats in self._counts.items()
        },
      }

  def reset(self) -> None:
    with self._lock:
      self._counts.clear()
      self._total_confirmations = 0
      self._prediction_log.clear()
      self._save()
    _logger.info("[Classifier] Reset complete")

# Singleton
_classifier: Optional[ProbabilisticClassifier] = None
_classifier_lock = threading.Lock()

def get_classifier() -> ProbabilisticClassifier:
  global _classifier
  with _classifier_lock:
    if _classifier is None:
      _classifier = ProbabilisticClassifier()
    return _classifier
