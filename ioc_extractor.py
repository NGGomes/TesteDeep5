"""
IOC Extractor - Extrai IPs, domínios e CVEs de texto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from core.logging import get_logger

_ioc_logger = get_logger("ioc_extractor")

_RE_IPV4 = re.compile(
  r"\b"
  r"(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.){3}"
  r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)"
  r"\b"
)

_RE_IPV6 = re.compile(
  r"\b"
  r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
  r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
  r"|:(?::[0-9a-fA-F]{1,4}){1,7}"
  r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"
  r"|::(?:[fF]{4}(?::0{1,4})?:)?"
  r"(?:(?:25[0-5]|(?:2[0-4]|1?\d)?\d)\.){3}"
  r"(?:25[0-5]|(?:2[0-4]|1?\d)?\d)"
  r"\b",
  re.VERBOSE,
)

_RE_FQDN = re.compile(
  r"\b"
  r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
  r"[a-zA-Z]{2,6}"
  r"\b"
)

_RE_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

_RE_PRIVATE_IPV4 = re.compile(
  r"^("
  r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
  r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
  r"192\.168\.\d{1,3}\.\d{1,3}|"
  r"127\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
  r"169\.254\.\d{1,3}\.\d{1,3}|"
  r"0\.0\.0\.0|"
  r"255\.255\.255\.255"
  r")$"
)

_INTERNAL_DOMAIN_SUFFIXES = (
  ".corp.local", ".corp.com", ".local", ".internal",
  ".lan", ".home", ".arpa",
)

_BENIGN_DOMAINS = frozenset({
  "all-corp-endpoints", "compliance-portal.corp.local",
})

def _is_private_ipv4(addr: str) -> bool:
  return bool(_RE_PRIVATE_IPV4.match(addr))

def _is_internal_fqdn(fqdn: str) -> bool:
  lower = fqdn.lower()
  return any(lower.endswith(suf) for suf in _INTERNAL_DOMAIN_SUFFIXES)

def _normalise_cve(raw: str) -> str:
  return raw.upper()

def _dedup(lst: List[str]) -> List[str]:
  seen: set = set()
  out: List[str] = []
  for item in lst:
    if item not in seen:
      seen.add(item)
      out.append(item)
  return out

@dataclass
class IOCBundle:
  ipv4_addresses: List[str] = field(default_factory=list)
  ipv6_addresses: List[str] = field(default_factory=list)
  fqdns: List[str] = field(default_factory=list)
  cve_ids: List[str] = field(default_factory=list)
  source_fields: List[str] = field(default_factory=list)

  def as_dict(self) -> dict:
    return {
      "ipv4_addresses": self.ipv4_addresses,
      "ipv6_addresses": self.ipv6_addresses,
      "fqdns": self.fqdns,
      "cve_ids": self.cve_ids,
      "source_fields": self.source_fields,
      "total_iocs": len(self.ipv4_addresses)
        + len(self.ipv6_addresses)
        + len(self.fqdns)
        + len(self.cve_ids),
    }

  def merge(self, other: "IOCBundle") -> "IOCBundle":
    return IOCBundle(
      ipv4_addresses=_dedup(self.ipv4_addresses + other.ipv4_addresses),
      ipv6_addresses=_dedup(self.ipv6_addresses + other.ipv6_addresses),
      fqdns=_dedup(self.fqdns + other.fqdns),
      cve_ids=_dedup(self.cve_ids + other.cve_ids),
      source_fields=_dedup(self.source_fields + other.source_fields),
    )

def _extract_from_text(text: str, field_name: str) -> IOCBundle:
  if not text:
    return IOCBundle()

  ipv4: List[str] = []
  ipv6: List[str] = []
  fqdns: List[str] = []
  cves: List[str] = []
  sources: List[str] = []

  for match in _RE_IPV4.finditer(text):
    addr = match.group(0)
    if not _is_private_ipv4(addr) and addr not in ipv4:
      ipv4.append(addr)

  for match in _RE_IPV6.finditer(text):
    addr = match.group(0)
    if addr not in ipv6:
      ipv6.append(addr)

  for match in _RE_FQDN.finditer(text):
    fqdn = match.group(0).rstrip(".")

    if _RE_IPV4.fullmatch(fqdn):
      continue

    if _is_internal_fqdn(fqdn):
      continue

    if fqdn.lower() in _BENIGN_DOMAINS:
      continue

    if fqdn not in fqdns:
      fqdns.append(fqdn)

  for match in _RE_CVE.finditer(text):
    cve = _normalise_cve(match.group(0))
    if cve not in cves:
      cves.append(cve)

  if ipv4 or ipv6 or fqdns or cves:
    sources.append(field_name)

  return IOCBundle(
    ipv4_addresses=ipv4,
    ipv6_addresses=ipv6,
    fqdns=fqdns,
    cve_ids=cves,
    source_fields=sources,
  )

def extract_iocs_from_alert(alert: dict) -> IOCBundle:
  bundle = IOCBundle()
  target_fields = ("Description", "AffectedAsset", "MitreAttack")

  for field_name in target_fields:
    raw = alert.get(field_name, "")
    if not isinstance(raw, str):
      raw = str(raw) if raw else ""

    if raw:
      partial = _extract_from_text(raw, field_name)
      bundle = bundle.merge(partial)

  bundle.ipv4_addresses = _dedup(bundle.ipv4_addresses)[:30]
  bundle.ipv6_addresses = _dedup(bundle.ipv6_addresses)[:30]
  bundle.fqdns = _dedup(bundle.fqdns)[:30]
  bundle.cve_ids = _dedup(bundle.cve_ids)[:20]
  bundle.source_fields = _dedup(bundle.source_fields)

  return bundle

def extract_iocs_from_alerts(alerts: List[dict]) -> IOCBundle:
  combined = IOCBundle()

  for alert in alerts:
    combined = combined.merge(extract_iocs_from_alert(alert))

  combined.ipv4_addresses = _dedup(combined.ipv4_addresses)[:30]
  combined.ipv6_addresses = _dedup(combined.ipv6_addresses)[:30]
  combined.fqdns = _dedup(combined.fqdns)[:30]
  combined.cve_ids = sorted(_dedup(combined.cve_ids))[:20]
  combined.source_fields = _dedup(combined.source_fields)

  return combined
