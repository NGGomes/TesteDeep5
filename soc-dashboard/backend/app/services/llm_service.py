""

from __future__ import annotations

import json as _json
import os
from typing import Tuple

import litellm
from loguru import logger

from app.core.config import settings

if settings.OPENAI_API_KEY:
 os.environ["OPENAI_API_KEY"]    = settings.OPENAI_API_KEY
if settings.ANTHROPIC_API_KEY:
 os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY

SYSTEM_PROMPT = ""

def _litellm_kwargs() -> dict:
 ""
 model = settings.ACTIVE_LLM_MODEL
 if not model:
  return {}

 provider = settings.LLM_PROVIDER.lower()

 if provider == "ollama":
  return {
   "model":    model,
   "api_base": settings.OLLAMA_BASE_URL,

   "api_key":  "ollama",
  }

 if provider == "anthropic":
  return {
   "model":   model,
   "api_key": settings.ANTHROPIC_API_KEY,
  }

 return {
  "model":   model,
  "api_key": settings.OPENAI_API_KEY or None,
 }

async def _call_llm(user_prompt: str) -> Tuple[str, str]:
 ""
 model = settings.ACTIVE_LLM_MODEL
 if not model:
  raise RuntimeError(
   "LLM is not configured. "
   "Set LLM_PROVIDER (and matching model/key vars) in your .env file."
  )

 kwargs = _litellm_kwargs()
 logger.info(f"LLM call → provider={settings.LLM_PROVIDER}  model={model}")

 try:
  response = await litellm.acompletion(
   **kwargs,
   messages=[
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": user_prompt},
   ],
   max_tokens=settings.MAX_TOKENS_PER_REQUEST,
   timeout=settings.LLM_TIMEOUT_SECONDS,
  )
  text = response.choices[0].message.content

  used = getattr(response, "model", model)
  logger.info(f"LLM response received  model_used={used}")
  return text, used

 except Exception as exc:
  logger.error(f"LLM call failed: {exc}")
  raise

async def analyze_cve(cve_data: dict, detail_level: str = "intermediate") -> str:
 ""
 level_map = {
  "basic":        "Usa linguagem acessível, adequada para um gestor não técnico.",
  "intermediate": "Usa linguagem técnica moderada, adequada para analista júnior.",
  "advanced":     "Usa linguagem altamente técnica para especialista em segurança.",
 }
 level_instruction = level_map.get(detail_level, level_map["intermediate"])

 cvss = cve_data.get("cvss", {})
 user_prompt = (
  f"Nível de detalhe: {level_instruction}\n\n"
  f"Analisa esta vulnerabilidade CVE:\n\n"
  f"ID              : {cve_data.get('id', 'N/A')}\n"
  f"Descrição (EN)  : {cve_data.get('description_en', 'N/A')}\n"
  f"CVSS Score      : {cvss.get('score', 'N/A')} ({cvss.get('severity', 'N/A')})\n"
  f"Vector          : {cvss.get('vector', 'N/A')}\n"
  f"Attack Vector   : {cvss.get('attack_vector', 'N/A')}\n"
  f"Priv. Required  : {cvss.get('privileges_required', 'N/A')}\n"
  f"Produtos afect. : {', '.join(cve_data.get('affected_products', [])[:5]) or 'N/A'}\n"
  f"CWEs            : {', '.join(cve_data.get('weaknesses', [])) or 'N/A'}\n"
  f"Publicado       : {cve_data.get('published', 'N/A')}\n\n"
  "Fornece uma análise 360° estruturada em markdown com as secções indicadas."
 )

 try:
  text, _ = await _call_llm(user_prompt)
  return text
 except RuntimeError as exc:
  return f"## LLM não configurado\n\n{exc}"
 except Exception as exc:
  logger.error(f"analyze_cve failed: {exc}")
  return (
   f"## Erro na análise\n\n"
   f"Não foi possível obter análise LLM: {exc}\n\n"
   f"**CVE**: {cve_data.get('id', 'N/A')}  \n"
   f"**CVSS**: {cvss.get('score', 'N/A')} {cvss.get('severity', '')}  \n"
   f"**Descrição**: {cve_data.get('description_en', 'N/A')}"
  )

async def analyze_siem_alert(alert_json: dict, detail_level: str = "intermediate") -> str:
 ""
 user_prompt = (
  f"Analisa este alerta SIEM do Elastic Security.\n\n"
  f"Alerta JSON:\n{_json.dumps(alert_json, indent=2, ensure_ascii=False)}\n\n"
  "Fornece uma análise de incidente estruturada em markdown com as secções: "
  "## Diagnóstico  ## Impacto  ## Acções Imediatas  ## MITRE ATT&CK"
 )

 try:
  text, _ = await _call_llm(user_prompt)
  return text
 except RuntimeError as exc:
  return f"## LLM não configurado\n\n{exc}"
 except Exception as exc:
  logger.error(f"analyze_siem_alert failed: {exc}")
  rule = alert_json.get("rule.name", alert_json.get("event.action", "unknown"))
  return (
   f"## Erro na análise\n\n"
   f"Não foi possível obter análise LLM: {exc}\n\n"
   f"**Regra**: {rule}  \n"
   f"**Severidade**: {alert_json.get('rule.severity', 'unknown')}"
  )

async def chat(
 messages: list[dict],
 max_tokens: int = 800,
) -> Tuple[str, str]:
 ""
 model = settings.ACTIVE_LLM_MODEL
 if not model:
  raise RuntimeError(
   "LLM is not configured. "
   "Set LLM_PROVIDER (and matching model/key vars) in your .env file."
  )

 kwargs = _litellm_kwargs()
 logger.info(f"Chat call → model={model}  messages={len(messages)}")

 try:
  response = await litellm.acompletion(
   **kwargs,
   messages=messages,
   max_tokens=max_tokens,
  )
  text = response.choices[0].message.content
  used = getattr(response, "model", model)
  return text, used
 except Exception as exc:
  logger.error(f"Chat call failed: {exc}")
  raise