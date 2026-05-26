""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings

CACHE_DIR    = Path("data/cve_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

def _cache_path(cve_id: str) -> Path:
 return CACHE_DIR / f"{cve_id.upper()}.json"

def _is_cache_valid(path: Path) -> bool:
 if not path.exists():
  return False
 age = time.time() - path.stat().st_mtime
 return age < settings.CVE_CACHE_TTL

async def fetch_cve(cve_id: str) -> Optional[dict]:
 cve_id     = cve_id.upper().strip()
 cache_file = _cache_path(cve_id)

 if _is_cache_valid(cache_file):
  logger.debug(f"Cache hit: {cve_id}")
  return json.loads(cache_file.read_text())

 logger.info(f"A consultar NVD para {cve_id}...")
 headers: dict = {}
 if settings.NVD_API_KEY:
  headers["apiKey"] = settings.NVD_API_KEY

 try:
  async with httpx.AsyncClient(timeout=settings.API_TIMEOUT_SECONDS) as client:
   resp = await client.get(
    NVD_BASE_URL,
    params={"cveId": cve_id},
    headers=headers,
   )
   resp.raise_for_status()
   data = resp.json()

  vulnerabilities = data.get("vulnerabilities", [])
  if not vulnerabilities:
   logger.warning(f"CVE não encontrado: {cve_id}")
   return None

  cve_data = vulnerabilities[0]["cve"]
  result   = _parse_cve(cve_data)
  cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
  logger.info(f"CVE {cve_id} guardado em cache.")
  return result

 except httpx.HTTPError as e:
  logger.error(f"Erro ao consultar NVD: {e}")
  return None

def _parse_cve(raw: dict) -> dict:
 descriptions = raw.get("descriptions", [])
 desc_pt = next((d["value"] for d in descriptions if d["lang"] == "pt"), None)
 desc_en = next((d["value"] for d in descriptions if d["lang"] == "en"), "N/A")

 metrics = raw.get("metrics", {})
 cvss: dict = {}
 if "cvssMetricV31" in metrics:
  m    = metrics["cvssMetricV31"][0]["cvssData"]
  cvss = {
   "version":            "3.1",
   "score":              m.get("baseScore"),
   "severity":           m.get("baseSeverity"),
   "vector":             m.get("vectorString"),
   "attack_vector":      m.get("attackVector"),
   "privileges_required":m.get("privilegesRequired"),
  }
 elif "cvssMetricV2" in metrics:
  m    = metrics["cvssMetricV2"][0]["cvssData"]
  cvss = {
   "version":  "2.0",
   "score":    m.get("baseScore"),
   "severity": metrics["cvssMetricV2"][0].get("baseSeverity"),
   "vector":   m.get("vectorString"),
  }

 configurations = raw.get("configurations", [])
 affected: list = []
 if configurations:
  nodes = configurations[0].get("nodes", [])
  if nodes:
   affected = [
    c["criteria"]
    for c in nodes[0].get("cpeMatch", [])
    if c.get("vulnerable")
   ]

 return {
  "id":              raw.get("id"),
  "published":       raw.get("published"),
  "last_modified":   raw.get("lastModified"),
  "description_en":  desc_en,
  "description_pt":  desc_pt,
  "cvss":            cvss,
  "affected_products": affected[:10],
  "references": [r["url"] for r in raw.get("references", [])[:5]],
  "weaknesses": [
   w["description"][0]["value"]
   for w in raw.get("weaknesses", [])
   if w.get("description")
  ],
 }