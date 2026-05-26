"""
Mapeamentos de fases ENISA, hipóteses CISO e configurações de risco.
"""

from typing import Dict, List, Tuple, Optional
from core.logging import get_logger

_mappings_logger = get_logger("agent1.mappings")

# ============================================================================
# ENISA PHASE MAPPING
# Cobre: categoria exacta, categoria genérica, variantes PT/EN, MITRE táctica
# ============================================================================

ENISA_PHASE_MAP: Dict[Tuple[str, str], Tuple[str, float]] = {

  # ── RECONNAISSANCE ──────────────────────────────────────────────────────────
  ("informationgathering", "scanning"):        ("RECON", 1.0),
  ("informationgathering", "reconnaissance"):  ("RECON", 1.0),
  ("informationgathering", "osint"):           ("RECON", 1.0),
  ("informationgathering", "enumeration"):     ("RECON", 1.0),
  ("informationgathering", "fingerprinting"):  ("RECON", 1.0),
  ("informationgathering", ""):                ("RECON", 1.0),
  ("recon", "scanning"):                       ("RECON", 1.0),
  ("recon", "reconnaissance"):                 ("RECON", 1.0),
  ("recon", "osint"):                          ("RECON", 1.0),
  ("recon", "enumeration"):                    ("RECON", 1.0),
  ("recon", ""):                               ("RECON", 1.0),
  ("reconnaissance", "scanning"):              ("RECON", 1.0),
  ("reconnaissance", ""):                      ("RECON", 1.0),
  ("scanning", ""):                            ("RECON", 1.0),
  ("scan", ""):                                ("RECON", 1.0),
  ("networkscan", ""):                         ("RECON", 1.0),
  ("portscan", ""):                            ("RECON", 1.0),
  # PT
  ("reconhecimento", ""):                      ("RECON", 1.0),
  ("pesquisa", ""):                            ("RECON", 1.0),

  # ── INITIAL ACCESS ──────────────────────────────────────────────────────────
  ("authentication", "login"):                          ("INITIAL_ACCESS", 3.0),
  ("authentication", "brute force"):                    ("INITIAL_ACCESS", 3.0),
  ("authentication", "bruteforce"):                     ("INITIAL_ACCESS", 3.0),
  ("authentication", "credential stuffing"):            ("INITIAL_ACCESS", 3.0),
  ("authentication", "mfa bypass"):                     ("INITIAL_ACCESS", 3.0),
  ("authentication", "phishing"):                       ("INITIAL_ACCESS", 3.0),
  ("authentication", "insider"):                        ("INITIAL_ACCESS", 3.0),
  ("authentication", ""):                               ("INITIAL_ACCESS", 3.0),
  ("intrusionattempts", "loginattempts"):                ("INITIAL_ACCESS", 3.0),
  ("intrusionattempts", "phishing"):                    ("INITIAL_ACCESS", 3.0),
  ("intrusionattempts", "exploitationofknownvulnerabilities"): ("INITIAL_ACCESS", 3.0),
  ("intrusionattempts", "exploit"):                     ("INITIAL_ACCESS", 3.0),
  ("intrusionattempts", "newattacksignature"):           ("INITIAL_ACCESS", 3.0),
  ("intrusionattempts", ""):                            ("INITIAL_ACCESS", 3.0),
  ("vulnerable", "exploit"):                            ("INITIAL_ACCESS", 3.0),
  ("vulnerable", "vulnerablesystem"):                   ("INITIAL_ACCESS", 3.0),
  ("vulnerable", "weakcrypto"):                         ("INITIAL_ACCESS", 3.0),
  ("vulnerable", "unwantedaccessibleservices"):         ("INITIAL_ACCESS", 3.0),
  ("vulnerable", ""):                                   ("INITIAL_ACCESS", 3.0),
  ("supplychaincompromise", "malware"):                  ("INITIAL_ACCESS", 3.0),
  ("supplychaincompromise", "vendor"):                   ("INITIAL_ACCESS", 3.0),
  ("supplychaincompromise", ""):                         ("INITIAL_ACCESS", 3.0),
  ("phishing", ""):                                     ("INITIAL_ACCESS", 3.5),
  ("spearphishing", ""):                                ("INITIAL_ACCESS", 3.5),
  ("initialaccess", ""):                                ("INITIAL_ACCESS", 3.0),
  ("initial access", ""):                               ("INITIAL_ACCESS", 3.0),
  ("initial_access", ""):                               ("INITIAL_ACCESS", 3.0),
  ("exploit", ""):                                      ("INITIAL_ACCESS", 3.5),
  ("exploitation", ""):                                 ("INITIAL_ACCESS", 3.5),
  ("credentialaccess", ""):                             ("INITIAL_ACCESS", 3.0),
  ("credential access", ""):                            ("INITIAL_ACCESS", 3.0),
  ("bruteforce", ""):                                   ("INITIAL_ACCESS", 3.0),
  ("brute force", ""):                                  ("INITIAL_ACCESS", 3.0),
  # PT
  ("acesso inicial", ""):                               ("INITIAL_ACCESS", 3.0),
  ("tentativa de intrusão", ""):                        ("INITIAL_ACCESS", 3.0),

  # ── EXECUTION ───────────────────────────────────────────────────────────────
  ("execution", "script"):                   ("EXECUTION", 4.0),
  ("execution", "command"):                  ("EXECUTION", 4.0),
  ("execution", "powershell"):               ("EXECUTION", 4.0),
  ("execution", "malware"):                  ("EXECUTION", 4.0),
  ("execution", "wmi"):                      ("EXECUTION", 4.0),
  ("execution", "macro"):                    ("EXECUTION", 4.0),
  ("execution", ""):                         ("EXECUTION", 4.0),
  ("malicioscode", "malware"):               ("EXECUTION", 4.0),
  ("malicioscode", "cryptominer"):           ("EXECUTION", 4.0),
  ("malicioscode", "ransomware"):            ("EXECUTION", 4.0),
  ("malicioscode", "loader"):                ("EXECUTION", 4.0),
  ("malicioscode", "c2"):                    ("EXECUTION", 4.0),
  ("malicioscode", "spyware"):               ("EXECUTION", 4.0),
  ("malicioscode", ""):                      ("EXECUTION", 4.0),
  ("malware", "ransomware"):                 ("EXECUTION", 4.5),
  ("malware", "trojan"):                     ("EXECUTION", 4.0),
  ("malware", "rat"):                        ("EXECUTION", 4.0),
  ("malware", "loader"):                     ("EXECUTION", 4.0),
  ("malware", "worm"):                       ("EXECUTION", 4.0),
  ("malware", "virus"):                      ("EXECUTION", 4.0),
  ("malware", "backdoor"):                   ("EXECUTION", 4.0),
  ("malware", "spyware"):                    ("EXECUTION", 4.0),
  ("malware", ""):                           ("EXECUTION", 4.0),
  ("ransomware", ""):                        ("EXECUTION", 4.5),
  ("commandcontrol", ""):                    ("EXECUTION", 4.0),
  ("command and control", ""):               ("EXECUTION", 4.0),
  ("c2", ""):                                ("EXECUTION", 4.0),
  ("c&c", ""):                               ("EXECUTION", 4.0),
  ("scriptexecution", ""):                   ("EXECUTION", 4.0),
  ("script execution", ""):                  ("EXECUTION", 4.0),
  # PT
  ("execução", ""):                          ("EXECUTION", 4.0),
  ("código malicioso", "malware"):           ("EXECUTION", 4.0),
  ("codigo malicioso", "malware"):           ("EXECUTION", 4.0),
  ("codigo malicioso", ""):                  ("EXECUTION", 4.0),

  # ── PERSISTENCE ─────────────────────────────────────────────────────────────
  ("persistence", "backdoor"):              ("PERSISTENCE", 6.0),
  ("persistence", "registry"):              ("PERSISTENCE", 6.0),
  ("persistence", "scheduled task"):        ("PERSISTENCE", 6.0),
  ("persistence", "scheduledtask"):         ("PERSISTENCE", 6.0),
  ("persistence", "startup"):               ("PERSISTENCE", 6.0),
  ("persistence", "service"):               ("PERSISTENCE", 6.0),
  ("persistence", "account"):               ("PERSISTENCE", 6.0),
  ("persistence", "bootkit"):               ("PERSISTENCE", 6.0),
  ("persistence", ""):                      ("PERSISTENCE", 6.0),
  ("backdoor", ""):                         ("PERSISTENCE", 6.0),
  ("scheduledtask", ""):                    ("PERSISTENCE", 6.0),
  ("registrypersistence", ""):              ("PERSISTENCE", 6.0),
  ("bootkitinstall", ""):                   ("PERSISTENCE", 6.0),
  # PT
  ("persistência", ""):                     ("PERSISTENCE", 6.0),

  # ── LATERAL MOVEMENT ────────────────────────────────────────────────────────
  ("discovery", "network"):                       ("LATERAL_MOVEMENT", 5.0),
  ("discovery", "smb"):                           ("LATERAL_MOVEMENT", 5.0),
  ("discovery", "enumeration"):                   ("LATERAL_MOVEMENT", 5.0),
  ("discovery", ""):                              ("LATERAL_MOVEMENT", 5.0),
  ("lateral_movement", "rdp"):                    ("LATERAL_MOVEMENT", 5.0),
  ("lateral_movement", "wmi"):                    ("LATERAL_MOVEMENT", 5.0),
  ("lateral_movement", "smb"):                    ("LATERAL_MOVEMENT", 5.0),
  ("lateral_movement", "ssh"):                    ("LATERAL_MOVEMENT", 5.0),
  ("lateral_movement", ""):                       ("LATERAL_MOVEMENT", 5.0),
  ("lateral movement", ""):                       ("LATERAL_MOVEMENT", 5.0),
  ("lateralmovement", ""):                        ("LATERAL_MOVEMENT", 5.0),
  ("intrusions", "systemcompromise"):             ("LATERAL_MOVEMENT", 5.0),
  ("intrusions", "applicationcompromise"):        ("LATERAL_MOVEMENT", 5.0),
  ("intrusions", ""):                             ("LATERAL_MOVEMENT", 5.0),
  ("intrusionattempts", "intrusionattempts"):      ("LATERAL_MOVEMENT", 5.0),
  ("privilegeescalation", ""):                    ("LATERAL_MOVEMENT", 5.0),
  ("privilege escalation", ""):                   ("LATERAL_MOVEMENT", 5.0),
  ("privilege_escalation", ""):                   ("LATERAL_MOVEMENT", 5.0),
  ("defenseevasion", ""):                         ("LATERAL_MOVEMENT", 4.5),
  ("defense evasion", ""):                        ("LATERAL_MOVEMENT", 4.5),
  ("passthehash", ""):                            ("LATERAL_MOVEMENT", 5.5),
  ("pass the hash", ""):                          ("LATERAL_MOVEMENT", 5.5),
  ("kerberoasting", ""):                          ("LATERAL_MOVEMENT", 5.5),
  ("rdp", ""):                                    ("LATERAL_MOVEMENT", 5.0),
  # PT
  ("movimento lateral", ""):                      ("LATERAL_MOVEMENT", 5.0),
  ("escalonamento de privilégios", ""):           ("LATERAL_MOVEMENT", 5.0),

  # ── EXFILTRATION ────────────────────────────────────────────────────────────
  ("exfiltration", "data"):                                ("EXFILTRATION", 7.0),
  ("exfiltration", "data leak"):                           ("EXFILTRATION", 7.0),
  ("exfiltration", "cloud"):                               ("EXFILTRATION", 7.0),
  ("exfiltration", "dns"):                                 ("EXFILTRATION", 7.0),
  ("exfiltration", "http"):                                ("EXFILTRATION", 7.0),
  ("exfiltration", "ftp"):                                 ("EXFILTRATION", 7.0),
  ("exfiltration", ""):                                    ("EXFILTRATION", 7.0),
  ("informationcontentsecurity", "unauthorisedaccesstoinformation"): ("EXFILTRATION", 7.0),
  ("informationcontentsecurity", ""):                      ("EXFILTRATION", 7.0),
  ("dataleak", ""):                                        ("EXFILTRATION", 7.0),
  ("data leak", ""):                                       ("EXFILTRATION", 7.0),
  ("databreach", ""):                                      ("EXFILTRATION", 7.0),
  ("data breach", ""):                                     ("EXFILTRATION", 7.0),
  ("collection", ""):                                      ("EXFILTRATION", 6.5),
  ("dnstunneling", ""):                                    ("EXFILTRATION", 7.5),
  ("dns tunneling", ""):                                   ("EXFILTRATION", 7.5),
  # PT
  ("exfiltração", ""):                                     ("EXFILTRATION", 7.0),
  ("segurança da informação", "data"):                     ("EXFILTRATION", 7.0),
  ("segurança da informação", ""):                         ("EXFILTRATION", 7.0),

  # ── IMPACT ──────────────────────────────────────────────────────────────────
  ("impact", "system"):          ("IMPACT", 8.0),
  ("impact", "ransomware"):      ("IMPACT", 8.0),
  ("impact", "wiper"):           ("IMPACT", 8.0),
  ("impact", "encryption"):      ("IMPACT", 8.0),
  ("impact", "ddos"):            ("IMPACT", 8.0),
  ("impact", "dos"):             ("IMPACT", 8.0),
  ("impact", "integrity"):       ("IMPACT", 8.0),
  ("impact", "defacement"):      ("IMPACT", 8.0),
  ("impact", "destruction"):     ("IMPACT", 8.0),
  ("impact", "cryptominer"):     ("IMPACT", 8.0),
  ("impact", ""):                ("IMPACT", 8.0),
  ("availability", "ddos"):      ("IMPACT", 8.0),
  ("availability", "dos"):       ("IMPACT", 8.0),
  ("availability", "flood"):     ("IMPACT", 8.0),
  ("availability", "disruption"):("IMPACT", 8.0),
  ("availability", ""):          ("IMPACT", 8.0),
  ("ddos", ""):                  ("IMPACT", 8.0),
  ("dos", ""):                   ("IMPACT", 7.5),
  ("wiper", ""):                 ("IMPACT", 9.0),
  ("wiperdeploy", ""):           ("IMPACT", 9.0),
  ("destructive", ""):           ("IMPACT", 8.5),
  ("datadestruction", ""):       ("IMPACT", 9.0),
  ("data destruction", ""):      ("IMPACT", 9.0),
  ("encryptedforimpact", ""):    ("IMPACT", 9.0),
  ("sabotage", "datadestruction"): ("IMPACT", 9.0),
  ("sabotage", ""):              ("IMPACT", 8.5),
  ("sabotagem", "destruição de dados"): ("IMPACT", 9.0),
  ("sabotagem", ""):             ("IMPACT", 8.5),
  # PT
  ("impacto", ""):               ("IMPACT", 8.0),

  # ── COMPLIANCE (maps to EXECUTION as closest kill-chain phase) ───────────────
  ("other", "compliance"):       ("EXECUTION", 4.0),
  ("other", "regulatory"):       ("EXECUTION", 4.0),
  ("other", "violation"):        ("EXECUTION", 4.0),
  ("compliance", "violation"):   ("EXECUTION", 4.0),
  ("compliance", "regulatory"):  ("EXECUTION", 4.0),
  ("compliance", ""):            ("EXECUTION", 4.0),
}

# ============================================================================
# PHASE WEIGHTS — used for phase_score calculation
# ============================================================================

PHASE_WEIGHTS: Dict[str, int] = {
  "RECON":            1,
  "INITIAL_ACCESS":   3,
  "EXECUTION":        4,
  "LATERAL_MOVEMENT": 5,
  "PERSISTENCE":      6,
  "EXFILTRATION":     7,
  "IMPACT":           8,
}

# ============================================================================
# PHASE PRIORITY — canonical kill-chain order for sorting
# ============================================================================

PHASE_PRIORITY: Dict[str, int] = {
  "RECON":            0,
  "INITIAL_ACCESS":   1,
  "EXECUTION":        2,
  "PERSISTENCE":      3,
  "LATERAL_MOVEMENT": 4,
  "EXFILTRATION":     5,
  "IMPACT":           6,
}

# ============================================================================
# CISO CATEGORIES — 16 canonical categories with tier, shortcode, keywords
# ============================================================================

CISO_CATEGORIES: Dict[int, dict] = {
  1: {
    "name": "Ransomware & Digital Extortion",
    "shortcode": "CRITICAL_RANSOMWARE",
    "risk_tier": "CRITICAL",
    "keywords": ["ransom", "lockbit", "conti", "revil", "blackcat", "extort",
                 "lockout", "decrypt", "encrypted for impact", "t1486"],
  },
  2: {
    "name": "Destructive Operations & Wipeware",
    "shortcode": "CRITICAL_DESTRUCTIVE",
    "risk_tier": "CRITICAL",
    "keywords": ["wiper", "destructive", "sabotage", "wipeware", "disk wipe",
                 "data destruction", "t1485"],
  },
  3: {
    "name": "Data Exfiltration & Corporate Espionage",
    "shortcode": "CRITICAL_EXFILTRATION",
    "risk_tier": "CRITICAL",
    "keywords": ["exfil", "data leak", "data breach", "corporate espionage",
                 "spyware", "infostealer", "rat", "remote access trojan",
                 "data theft", "t1041", "t1048", "t1567"],
  },
  4: {
    "name": "Credential & Identity Compromise",
    "shortcode": "HIGH_CREDENTIAL",
    "risk_tier": "HIGH",
    "keywords": ["credential", "brute force", "password spray", "mfa fatigue",
                 "account takeover", "kerberoast", "pass-the-hash",
                 "golden ticket", "dcsync", "lsass", "mimikatz", "ntlm",
                 "t1110", "t1003", "t1558"],
  },
  5: {
    "name": "Advanced Persistent Threats (APT)",
    "shortcode": "HIGH_APT",
    "risk_tier": "HIGH",
    "keywords": ["apt", "nation-state", "state-sponsored", "lotl",
                 "living-off-the-land", "fileless", "cozy bear", "fancy bear",
                 "apt29", "apt28", "turla", "lazarus", "t1059"],
  },
  6: {
    "name": "Supply Chain & Third-Party Compromise",
    "shortcode": "HIGH_SUPPLY_CHAIN",
    "risk_tier": "HIGH",
    "keywords": ["supply chain", "supply_chain", "third party", "third-party",
                 "vendor", "dependency confusion", "tampered",
                 "malicious update", "t1195", "t1199"],
  },
  7: {
    "name": "Critical Service Disruption — DDoS",
    "shortcode": "HIGH_DDOS",
    "risk_tier": "HIGH",
    "keywords": ["ddos", "dos", "denial of service", "flood", "amplification",
                 "volumetric", "botnet flood", "t1498", "t1499"],
  },
  8: {
    "name": "Social Engineering, Phishing & BEC",
    "shortcode": "MED_HIGH_PHISHING",
    "risk_tier": "MEDIUM-HIGH",
    "keywords": ["phishing", "spear phishing", "bec",
                 "business email compromise", "social engineering",
                 "vishing", "smishing", "impersonation", "whaling",
                 "t1566", "t1534"],
  },
  9: {
    "name": "System & Application Vulnerability Exploitation",
    "shortcode": "MED_HIGH_EXPLOIT",
    "risk_tier": "MEDIUM-HIGH",
    "keywords": ["vulnerab", "cve-", "exploit", "zero-day", "sql injection",
                 "xss", "rce", "remote code exec", "webshell", "web shell",
                 "t1190", "t1203", "t1211"],
  },
  10: {
    "name": "Information Manipulation & Integrity Attacks",
    "shortcode": "MEDIUM_INTEGRITY",
    "risk_tier": "MEDIUM",
    "keywords": ["integrity", "manipulation", "defacement", "disinformation",
                 "database tampering", "record alteration", "t1491", "t1565"],
  },
  11: {
    "name": "Insider Threats & Physical Security Breaches",
    "shortcode": "MEDIUM_INSIDER",
    "risk_tier": "MEDIUM",
    "keywords": ["insider", "disgruntled", "physical intrusion", "burglary",
                 "unauthorized_access", "privileged_account_abuse",
                 "after hours", "t1078"],
  },
  12: {
    "name": "Regulatory & Compliance Violations",
    "shortcode": "MEDIUM_COMPLIANCE",
    "risk_tier": "MEDIUM",
    "keywords": ["compliance", "regulatory", "nis2", "gdpr", "dora", "pci",
                 "hipaa", "audit finding", "breach notification", "t1562"],
  },
  13: {
    "name": "Cryptojacking & Unauthorized Resource Abuse",
    "shortcode": "LOW_MED_CRYPTOJACK",
    "risk_tier": "LOW-MED",
    "keywords": ["cryptominer", "cryptojacking", "xmrig", "monero",
                 "resource hijacking", "unauthorized mining", "t1496"],
  },
  14: {
    "name": "Malware Infrastructure & Botnet Activity",
    "shortcode": "LOW_MED_BOTNET",
    "risk_tier": "LOW-MED",
    "keywords": ["botnet", "c2", "command and control", "beacon",
                 "cobalt strike", "loader", "generic malware",
                 "t1071", "t1105", "t1102"],
  },
  15: {
    "name": "Reconnaissance & Pre-Attack Intelligence Gathering",
    "shortcode": "LOW_RECON",
    "risk_tier": "LOW",
    "keywords": ["scan", "scanning", "reconnaissance", "recon", "osint",
                 "footprint", "enumerat", "t1595", "t1590", "t1592"],
  },
  16: {
    "name": "Others",
    "shortcode": "OTHER",
    "risk_tier": "—",
    "keywords": ["spam", "harmful speech", "uncategorised", "other"],
  },
}

# ── Derived list of canonical category names (used by BayesianMarkovClassifier)
CISO_CATEGORIES_LIST: List[str] = [v["name"] for v in CISO_CATEGORIES.values()]

# ============================================================================
# CISO CATEGORY WEIGHTS — for phase_score calculation
# ============================================================================

CISO_CATEGORY_WEIGHTS: Dict[int, float] = {
  1: 10.0, 2: 10.0, 3: 9.0,  4: 7.0,  5: 7.0,
  6:  7.0, 7:  6.0, 8: 5.0,  9: 5.0, 10: 4.0,
  11: 4.0, 12: 4.0, 13: 3.0, 14: 3.0, 15: 1.0, 16: 0.5,
}

# ============================================================================
# SCORE TO CISO STATE — severity thresholds
# ============================================================================

SCORE_TO_CISO_STATE: Dict[Tuple[int, int], Tuple[str, str]] = {
  (0,  0):   ("RUIDO_OPERACIONAL",      "No significant activity"),
  (1,  2):   ("RUIDO_OPERACIONAL",      "Operational noise"),
  (3,  4):   ("ATIVIDADE_SUSPEITA",     "Suspicious activity"),
  (5,  9):   ("INCIDENTE_SEGURANCA",    "Security incident"),
  (10, 14):  ("INCIDENTE_GRAVE",        "Serious incident"),
  (15, 999): ("CRITICAL_COMBINED_ATTACK", "Critical combined attack"),
}

# ============================================================================
# PHASE TO CISO CATEGORY — primary mapping (single-phase fallback)
# ============================================================================

PHASE_TO_CISO_CATEGORY: Dict[str, int] = {
  "RECON":            15,  # Reconnaissance
  "INITIAL_ACCESS":    4,  # Credential compromise
  "EXECUTION":        14,  # Malware/Botnet
  "LATERAL_MOVEMENT":  5,  # APT
  "PERSISTENCE":       5,  # APT
  "EXFILTRATION":      3,  # Data exfiltration
  "IMPACT":            1,  # Ransomware
}

# ============================================================================
# PHASE TO SECONDARY CISO CATEGORIES — for multi-hypothesis generation
# ============================================================================

PHASE_TO_SECONDARY_CISO_CATEGORIES: Dict[str, List[int]] = {
  "RECON":            [],
           # only primary
  "INITIAL_ACCESS":   [8, 9],
           # Phishing + Vulnerability
  "EXECUTION":        [9, 13],
           # Vulnerability + Cryptojacking
  "LATERAL_MOVEMENT": [4, 11],
           # Credential + Insider
  "PERSISTENCE":      [11],
           # Insider
  "EXFILTRATION":     [11, 12],
           # Insider + Compliance
  "IMPACT":           [2, 7, 10],
           # Destructive + DDoS + Integrity
}

# ============================================================================
# CISO CATEGORY MIN STATE — minimum CISO state elevation per category
# ============================================================================

CISO_CATEGORY_MIN_STATE: Dict[int, str] = {
  1:  "CRITICAL_COMBINED_ATTACK",  # Ransomware
  2:  "CRITICAL_COMBINED_ATTACK",  # Destructive
  3:  "INCIDENTE_GRAVE",           # Exfiltration
  4:  "INCIDENTE_SEGURANCA",       # Credential
  5:  "INCIDENTE_GRAVE",           # APT
  6:  "INCIDENTE_SEGURANCA",       # Supply Chain
  7:  "INCIDENTE_SEGURANCA",       # DDoS
  8:  "ATIVIDADE_SUSPEITA",        # Phishing
  9:  "RUIDO_OPERACIONAL",         # Vulnerability
  10: "ATIVIDADE_SUSPEITA",        # Integrity
  11: "ATIVIDADE_SUSPEITA",        # Insider
  12: "ATIVIDADE_SUSPEITA",        # Compliance
  13: "RUIDO_OPERACIONAL",         # Cryptojacking
  14: "RUIDO_OPERACIONAL",         # Botnet
  15: "RUIDO_OPERACIONAL",         # Recon
  16: "RUIDO_OPERACIONAL",         # Others
}

# ============================================================================
# CISO STATE ORDER — for comparison/ordering
# ============================================================================

CISO_STATE_ORDER: Dict[str, int] = {
  "RUIDO_OPERACIONAL":      0,
  "ATIVIDADE_SUSPEITA":     1,
  "INCIDENTE_SEGURANCA":    2,
  "INCIDENTE_GRAVE":        3,
  "CRITICAL_COMBINED_ATTACK": 4,
}

# ============================================================================
# ADAPTIVE WINDOW — exported constants (used by agent1/core.py)
# ============================================================================

ADAPTIVE_EXTENSION_MINUTES: int     = 5   # minutes to extend window per high-weight alert
ADAPTIVE_EXTENSION_WEIGHT_MIN: float = 5.0 # min phase weight to trigger extension

# ============================================================================
# MITRE ATT&CK DETAILS — per CISO category
# ============================================================================

_CISO_TO_MITRE_DETAIL: Dict[int, Dict] = {
  1:  {"tech": "T1486", "name": "Data Encrypted for Impact",
       "tactic": "TA0040-Impact",              "mitigation": "M1053 - Data Backup"},
  2:  {"tech": "T1485", "name": "Data Destruction",
       "tactic": "TA0040-Impact",              "mitigation": "M1053 - Data Backup; M1040 - Behavior Prevention"},
  3:  {"tech": "T1041", "name": "Exfiltration Over C2 Channel",
       "tactic": "TA0010-Exfiltration",        "mitigation": "M1057 - Data Loss Prevention"},
  4:  {"tech": "T1110", "name": "Brute Force",
       "tactic": "TA0006-Credential Access",   "mitigation": "M1032 - Multi-factor Authentication"},
  5:  {"tech": "T1059", "name": "Command & Scripting Interpreter",
       "tactic": "TA0002-Execution",           "mitigation": "M1045 - Code Signing"},
  6:  {"tech": "T1195", "name": "Supply Chain Compromise",
       "tactic": "TA0001-Initial Access",      "mitigation": "M1051 - Update Software"},
  7:  {"tech": "T1498", "name": "Network Denial of Service",
       "tactic": "TA0040-Impact",              "mitigation": "M1037 - Filter Network Traffic"},
  8:  {"tech": "T1566", "name": "Phishing",
       "tactic": "TA0001-Initial Access",      "mitigation": "M1049 - Antivirus/Antimalware; M1017 - User Training"},
  9:  {"tech": "T1190", "name": "Exploit Public-Facing Application",
       "tactic": "TA0001-Initial Access",      "mitigation": "M1048 - Application Isolation; M1051 - Update Software"},
  10: {"tech": "T1565", "name": "Data Manipulation",
       "tactic": "TA0040-Impact",              "mitigation": "M1041 - Encrypt Sensitive Information"},
  11: {"tech": "T1078", "name": "Valid Accounts (Insider)",
       "tactic": "TA0003-Persistence",         "mitigation": "M1026 - Privileged Account Management"},
  12: {"tech": "T1562", "name": "Impair Defenses",
       "tactic": "TA0005-Defense Evasion",     "mitigation": "M1047 - Audit; M1018 - User Account Management"},
  13: {"tech": "T1496", "name": "Resource Hijacking",
       "tactic": "TA0040-Impact",              "mitigation": "M1018 - User Account Management"},
  14: {"tech": "T1071", "name": "Application Layer Protocol (C2)",
       "tactic": "TA0011-Command & Control",   "mitigation": "M1031 - Network Intrusion Prevention"},
  15: {"tech": "T1595", "name": "Active Scanning",
       "tactic": "TA0043-Reconnaissance",      "mitigation": "M1056 - Pre-compromise"},
  16: {"tech": "—",     "name": "Uncategorised",
       "tactic": "—",                          "mitigation": "—"},
}

def get_mitre_detail(cat_id: int) -> dict:
  """Return MITRE detail for a CISO category."""
  return _CISO_TO_MITRE_DETAIL.get(cat_id, _CISO_TO_MITRE_DETAIL[16])

# ============================================================================
# KEYWORD TO CISO CATEGORY — fallback classification by keyword
# ============================================================================

KEYWORD_TO_CISO_CATEGORY: List[Tuple[List[str], int]] = [
  # 1 - Ransomware & Digital Extortion
  (["ransom", "lockbit", "conti", "revil", "blackcat", "extort", "lockout",
    "decrypt", "encrypted for impact", "t1486"], 1),
  # 2 - Destructive Operations & Wipeware
  (["wiper", "destructive", "sabotage", "wipeware", "disk wipe",
    "data destruction", "t1485"], 2),
  # 3 - Data Exfiltration & Corporate Espionage
  (["exfil", "data leak", "data breach", "corporate espionage", "spyware",
    "infostealer", "rat", "remote access trojan", "data theft",
    "t1041", "t1048", "t1567"], 3),
  # 4 - Credential & Identity Compromise
  (["credential", "brute force", "password spray", "mfa fatigue",
    "account takeover", "kerberoast", "pass-the-hash", "golden ticket",
    "dcsync", "lsass", "mimikatz", "ntlm", "t1110", "t1003", "t1558"], 4),
  # 5 - Advanced Persistent Threats (APT)
  (["apt", "nation-state", "state-sponsored", "lotl", "living-off-the-land",
    "fileless", "cozy bear", "fancy bear", "apt29", "apt28", "turla",
    "lazarus", "t1059"], 5),
  # 6 - Supply Chain & Third-Party Compromise
  (["supply chain", "supply_chain", "third party", "third-party", "vendor",
    "dependency confusion", "tampered", "malicious update", "t1195", "t1199"], 6),
  # 7 - Critical Service Disruption — DDoS
  (["ddos", "dos", "denial of service", "flood", "amplification",
    "volumetric", "botnet flood", "t1498", "t1499"], 7),
  # 8 - Social Engineering, Phishing & BEC
  (["phishing", "spear phishing", "bec", "business email compromise",
    "social engineering", "vishing", "smishing", "impersonation",
    "whaling", "t1566", "t1534"], 8),
  # 9 - System & Application Vulnerability Exploitation
  (["vulnerab", "cve-", "exploit", "zero-day", "sql injection", "xss",
    "rce", "remote code exec", "webshell", "web shell",
    "t1190", "t1203", "t1211"], 9),
  # 10 - Information Manipulation & Integrity Attacks
  (["integrity", "manipulation", "defacement", "disinformation",
    "database tampering", "record alteration", "t1491", "t1565"], 10),
  # 11 - Insider Threats & Physical Security Breaches
  (["insider", "disgruntled", "physical intrusion", "burglary",
    "unauthorized_access", "privileged_account_abuse",
    "after hours", "t1078"], 11),
  # 12 - Regulatory & Compliance Violations
  (["compliance", "regulatory", "nis2", "gdpr", "dora", "pci", "hipaa",
    "audit finding", "breach notification", "t1562"], 12),
  # 13 - Cryptojacking & Unauthorized Resource Abuse
  (["cryptominer", "cryptojacking", "xmrig", "monero",
    "resource hijacking", "unauthorized mining", "t1496"], 13),
  # 14 - Malware Infrastructure & Botnet Activity
  (["botnet", "c2", "command and control", "beacon", "cobalt strike",
    "loader", "generic malware", "t1071", "t1105", "t1102"], 14),
  # 15 - Reconnaissance & Pre-Attack Intelligence Gathering
  (["scan", "scanning", "reconnaissance", "recon", "osint",
    "footprint", "enumerat", "t1595", "t1590", "t1592"], 15),
  # 16 - Others
  (["spam", "harmful speech", "uncategorised", "other"], 16),
]

# ============================================================================
# SEQUENCE TO CISO — static priors for phase sequences
# All labels must be canonical CISO_CATEGORIES names
# ============================================================================

SEQUENCE_TO_CISO: Dict[Tuple[str, ...], List[Tuple[str, float]]] = {

  # ── Single phase ─────────────────────────────────────────────────────────────
  ("RECON",): [
    ("Reconnaissance & Pre-Attack Intelligence Gathering", 0.85),
    ("Malware Infrastructure & Botnet Activity",           0.10),
    ("Others",                                             0.05),
  ],
  ("INITIAL_ACCESS",): [
    ("Credential & Identity Compromise",                   0.70),
    ("System & Application Vulnerability Exploitation",    0.20),
    ("Social Engineering, Phishing & BEC",                 0.10),
  ],
  ("EXECUTION",): [
    ("Malware Infrastructure & Botnet Activity",           0.65),
    ("Cryptojacking & Unauthorized Resource Abuse",        0.20),
    ("Advanced Persistent Threats (APT)",                  0.15),
  ],
  ("PERSISTENCE",): [
    ("Advanced Persistent Threats (APT)",                  0.75),
    ("Insider Threats & Physical Security Breaches",       0.15),
    ("Malware Infrastructure & Botnet Activity",           0.10),
  ],
  ("LATERAL_MOVEMENT",): [
    ("Advanced Persistent Threats (APT)",                  0.65),
    ("Credential & Identity Compromise",                   0.25),
    ("Insider Threats & Physical Security Breaches",       0.10),
  ],
  ("EXFILTRATION",): [
    ("Data Exfiltration & Corporate Espionage",            0.85),
    ("Insider Threats & Physical Security Breaches",       0.10),
    ("Others",                                             0.05),
  ],
  ("IMPACT",): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Destructive Operations & Wipeware",                  0.20),
    ("Critical Service Disruption — DDoS",                 0.05),
  ],

  # ── Two phases ───────────────────────────────────────────────────────────────
  ("RECON", "INITIAL_ACCESS"): [
    ("Advanced Persistent Threats (APT)",                  0.65),
    ("Credential & Identity Compromise",                   0.25),
    ("System & Application Vulnerability Exploitation",    0.10),
  ],
  ("RECON", "EXECUTION"): [
    ("Malware Infrastructure & Botnet Activity",           0.70),
    ("Advanced Persistent Threats (APT)",                  0.20),
    ("Cryptojacking & Unauthorized Resource Abuse",        0.10),
  ],
  ("RECON", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.70),
    ("Critical Service Disruption — DDoS",                 0.20),
    ("Destructive Operations & Wipeware",                  0.10),
  ],
  ("INITIAL_ACCESS", "EXECUTION"): [
    ("Malware Infrastructure & Botnet Activity",           0.60),
    ("System & Application Vulnerability Exploitation",    0.25),
    ("Advanced Persistent Threats (APT)",                  0.15),
  ],
  ("INITIAL_ACCESS", "PERSISTENCE"): [
    ("Advanced Persistent Threats (APT)",                  0.75),
    ("Credential & Identity Compromise",                   0.15),
    ("Malware Infrastructure & Botnet Activity",           0.10),
  ],
  ("INITIAL_ACCESS", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.70),
    ("Credential & Identity Compromise",                   0.20),
    ("Insider Threats & Physical Security Breaches",       0.10),
  ],
  ("INITIAL_ACCESS", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.75),
    ("Insider Threats & Physical Security Breaches",       0.15),
    ("Advanced Persistent Threats (APT)",                  0.10),
  ],
  ("EXECUTION", "PERSISTENCE"): [
    ("Advanced Persistent Threats (APT)",                  0.65),
    ("Malware Infrastructure & Botnet Activity",           0.25),
    ("Insider Threats & Physical Security Breaches",       0.10),
  ],
  ("EXECUTION", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.70),
    ("Malware Infrastructure & Botnet Activity",           0.20),
    ("Credential & Identity Compromise",                   0.10),
  ],
  ("EXECUTION", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.70),
    ("Malware Infrastructure & Botnet Activity",           0.20),
    ("Advanced Persistent Threats (APT)",                  0.10),
  ],
  ("EXECUTION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Destructive Operations & Wipeware",                  0.20),
    ("Others",                                             0.05),
  ],
  ("PERSISTENCE", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.80),
    ("Credential & Identity Compromise",                   0.15),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("PERSISTENCE", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.70),
    ("Advanced Persistent Threats (APT)",                  0.20),
    ("Insider Threats & Physical Security Breaches",       0.10),
  ],
  ("PERSISTENCE", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Destructive Operations & Wipeware",                  0.20),
    ("Advanced Persistent Threats (APT)",                  0.05),
  ],
  ("LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.80),
    ("Advanced Persistent Threats (APT)",                  0.15),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.65),
    ("Destructive Operations & Wipeware",                  0.25),
    ("Advanced Persistent Threats (APT)",                  0.10),
  ],
  ("EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Data Exfiltration & Corporate Espionage",            0.20),
    ("Destructive Operations & Wipeware",                  0.05),
  ],

  # ── Three phases ─────────────────────────────────────────────────────────────
  ("RECON", "INITIAL_ACCESS", "EXECUTION"): [
    ("Advanced Persistent Threats (APT)",                  0.65),
    ("System & Application Vulnerability Exploitation",    0.25),
    ("Malware Infrastructure & Botnet Activity",           0.10),
  ],
  ("RECON", "INITIAL_ACCESS", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.80),
    ("Credential & Identity Compromise",                   0.15),
    ("Others",                                             0.05),
  ],
  ("RECON", "INITIAL_ACCESS", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.70),
    ("Critical Service Disruption — DDoS",                 0.20),
    ("Destructive Operations & Wipeware",                  0.10),
  ],
  ("RECON", "EXECUTION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Destructive Operations & Wipeware",                  0.15),
    ("Malware Infrastructure & Botnet Activity",           0.10),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "PERSISTENCE"): [
    ("Advanced Persistent Threats (APT)",                  0.70),
    ("Malware Infrastructure & Botnet Activity",           0.20),
    ("Credential & Identity Compromise",                   0.10),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.75),
    ("Credential & Identity Compromise",                   0.15),
    ("Malware Infrastructure & Botnet Activity",           0.10),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Destructive Operations & Wipeware",                  0.15),
    ("Advanced Persistent Threats (APT)",                  0.10),
  ],
  ("INITIAL_ACCESS", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.80),
    ("Advanced Persistent Threats (APT)",                  0.15),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("INITIAL_ACCESS", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.70),
    ("Destructive Operations & Wipeware",                  0.20),
    ("Advanced Persistent Threats (APT)",                  0.10),
  ],
  ("INITIAL_ACCESS", "PERSISTENCE", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.75),
    ("Advanced Persistent Threats (APT)",                  0.20),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("EXECUTION", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.75),
    ("Advanced Persistent Threats (APT)",                  0.20),
    ("Malware Infrastructure & Botnet Activity",           0.05),
  ],
  ("EXECUTION", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.75),
    ("Destructive Operations & Wipeware",                  0.20),
    ("Advanced Persistent Threats (APT)",                  0.05),
  ],
  ("EXECUTION", "PERSISTENCE", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.80),
    ("Destructive Operations & Wipeware",                  0.15),
    ("Advanced Persistent Threats (APT)",                  0.05),
  ],
  ("PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.75),
    ("Advanced Persistent Threats (APT)",                  0.20),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("PERSISTENCE", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.70),
    ("Destructive Operations & Wipeware",                  0.20),
    ("Advanced Persistent Threats (APT)",                  0.10),
  ],
  ("LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.80),
    ("Data Exfiltration & Corporate Espionage",            0.15),
    ("Destructive Operations & Wipeware",                  0.05),
  ],

  # ── Four phases ──────────────────────────────────────────────────────────────
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE"): [
    ("Advanced Persistent Threats (APT)",                  0.80),
    ("Supply Chain & Third-Party Compromise",              0.12),
    ("Malware Infrastructure & Botnet Activity",           0.08),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.82),
    ("Credential & Identity Compromise",                   0.12),
    ("Malware Infrastructure & Botnet Activity",           0.06),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.80),
    ("Destructive Operations & Wipeware",                  0.15),
    ("Advanced Persistent Threats (APT)",                  0.05),
  ],
  ("RECON", "INITIAL_ACCESS", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.82),
    ("Advanced Persistent Threats (APT)",                  0.13),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("RECON", "INITIAL_ACCESS", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.80),
    ("Destructive Operations & Wipeware",                  0.14),
    ("Advanced Persistent Threats (APT)",                  0.06),
  ],
  ("RECON", "INITIAL_ACCESS", "PERSISTENCE", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.78),
    ("Advanced Persistent Threats (APT)",                  0.15),
    ("Destructive Operations & Wipeware",                  0.07),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.85),
    ("Advanced Persistent Threats (APT)",                  0.10),
    ("Malware Infrastructure & Botnet Activity",           0.05),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.82),
    ("Destructive Operations & Wipeware",                  0.13),
    ("Advanced Persistent Threats (APT)",                  0.05),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.82),
    ("Advanced Persistent Threats (APT)",                  0.12),
    ("Destructive Operations & Wipeware",                  0.06),
  ],
  ("INITIAL_ACCESS", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.80),
    ("Advanced Persistent Threats (APT)",                  0.15),
    ("Insider Threats & Physical Security Breaches",       0.05),
  ],
  ("EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.78),
    ("Advanced Persistent Threats (APT)",                  0.17),
    ("Malware Infrastructure & Botnet Activity",           0.05),
  ],
  ("EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.82),
    ("Destructive Operations & Wipeware",                  0.13),
    ("Advanced Persistent Threats (APT)",                  0.05),
  ],
  ("PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.85),
    ("Data Exfiltration & Corporate Espionage",            0.10),
    ("Destructive Operations & Wipeware",                  0.05),
  ],

  # ── Five phases ──────────────────────────────────────────────────────────────
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT"): [
    ("Advanced Persistent Threats (APT)",                  0.88),
    ("Supply Chain & Third-Party Compromise",              0.08),
    ("Malware Infrastructure & Botnet Activity",           0.04),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.88),
    ("Advanced Persistent Threats (APT)",                  0.09),
    ("Others",                                             0.03),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.87),
    ("Destructive Operations & Wipeware",                  0.09),
    ("Advanced Persistent Threats (APT)",                  0.04),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.85),
    ("Advanced Persistent Threats (APT)",                  0.10),
    ("Destructive Operations & Wipeware",                  0.05),
  ],
  ("RECON", "INITIAL_ACCESS", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.85),
    ("Advanced Persistent Threats (APT)",                  0.12),
    ("Insider Threats & Physical Security Breaches",       0.03),
  ],
  ("RECON", "INITIAL_ACCESS", "PERSISTENCE", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.85),
    ("Advanced Persistent Threats (APT)",                  0.10),
    ("Destructive Operations & Wipeware",                  0.05),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.87),
    ("Advanced Persistent Threats (APT)",                  0.10),
    ("Others",                                             0.03),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.87),
    ("Destructive Operations & Wipeware",                  0.09),
    ("Advanced Persistent Threats (APT)",                  0.04),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.88),
    ("Data Exfiltration & Corporate Espionage",            0.08),
    ("Destructive Operations & Wipeware",                  0.04),
  ],
  ("EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.88),
    ("Data Exfiltration & Corporate Espionage",            0.08),
    ("Destructive Operations & Wipeware",                  0.04),
  ],

  # ── Six phases ───────────────────────────────────────────────────────────────
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION"): [
    ("Data Exfiltration & Corporate Espionage",            0.88),
    ("Advanced Persistent Threats (APT)",                  0.09),
    ("Ransomware & Digital Extortion",                     0.03),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.88),
    ("Destructive Operations & Wipeware",                  0.08),
    ("Advanced Persistent Threats (APT)",                  0.04),
  ],
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.90),
    ("Data Exfiltration & Corporate Espionage",            0.07),
    ("Destructive Operations & Wipeware",                  0.03),
  ],
  ("INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.90),
    ("Data Exfiltration & Corporate Espionage",            0.07),
    ("Destructive Operations & Wipeware",                  0.03),
  ],

  # ── Full kill chain (all 7 phases) ───────────────────────────────────────────
  ("RECON", "INITIAL_ACCESS", "EXECUTION", "PERSISTENCE", "LATERAL_MOVEMENT", "EXFILTRATION", "IMPACT"): [
    ("Ransomware & Digital Extortion",                     0.92),
    ("Data Exfiltration & Corporate Espionage",            0.05),
    ("Destructive Operations & Wipeware",                  0.03),
  ],
}

# ============================================================================
# Helper functions
# ============================================================================

# Backward-compat alias
ENISA_TO_PHASE = ENISA_PHASE_MAP

# ── MITRE ATT&CK technique → kill-chain phase mapping ────────────────────────
MITRE_TO_PHASE: Dict[str, Tuple[str, float]] = {
  # Reconnaissance
  "T1595": ("RECON", 1.5), "T1592": ("RECON", 1.5), "T1589": ("RECON", 1.5),
  "T1590": ("RECON", 1.5), "T1591": ("RECON", 1.5), "T1598": ("RECON", 1.5),
  "T1597": ("RECON", 1.0), "T1596": ("RECON", 1.0),
  # Initial Access
  "T1566": ("INITIAL_ACCESS", 3.5), "T1190": ("INITIAL_ACCESS", 3.5),
  "T1133": ("INITIAL_ACCESS", 3.0), "T1078": ("INITIAL_ACCESS", 3.0),
  "T1091": ("INITIAL_ACCESS", 3.0), "T1195": ("INITIAL_ACCESS", 3.5),
  "T1199": ("INITIAL_ACCESS", 3.0), "T1200": ("INITIAL_ACCESS", 2.5),
  # Execution
  "T1059": ("EXECUTION", 4.5), "T1204": ("EXECUTION", 4.0),
  "T1047": ("EXECUTION", 4.0), "T1053": ("EXECUTION", 4.0),
  "T1569": ("EXECUTION", 4.0), "T1129": ("EXECUTION", 3.5),
  "T1106": ("EXECUTION", 4.0), "T1203": ("EXECUTION", 4.5),
  # Persistence
  "T1547": ("PERSISTENCE", 6.0), "T1543": ("PERSISTENCE", 6.0),
  "T1546": ("PERSISTENCE", 6.0), "T1197": ("PERSISTENCE", 5.5),
  "T1136": ("PERSISTENCE", 6.0), "T1505": ("PERSISTENCE", 6.5),
  "T1098": ("PERSISTENCE", 6.0), "T1556": ("PERSISTENCE", 6.0),
  # Privilege Escalation / Defence Evasion → Lateral Movement weight
  "T1055": ("LATERAL_MOVEMENT", 5.0), "T1134": ("LATERAL_MOVEMENT", 5.0),
  "T1484": ("LATERAL_MOVEMENT", 5.5),
  # Lateral Movement
  "T1021": ("LATERAL_MOVEMENT", 5.5), "T1570": ("LATERAL_MOVEMENT", 5.0),
  "T1550": ("LATERAL_MOVEMENT", 5.5), "T1563": ("LATERAL_MOVEMENT", 5.0),
  "T1534": ("LATERAL_MOVEMENT", 5.0), "T1210": ("LATERAL_MOVEMENT", 5.5),
  # Collection / Exfiltration
  "T1560": ("EXFILTRATION", 6.5), "T1005": ("EXFILTRATION", 6.5),
  "T1039": ("EXFILTRATION", 6.5), "T1041": ("EXFILTRATION", 7.5),
  "T1048": ("EXFILTRATION", 7.5), "T1567": ("EXFILTRATION", 7.5),
  "T1052": ("EXFILTRATION", 7.0), "T1537": ("EXFILTRATION", 7.0),
  # Impact
  "T1485": ("IMPACT", 9.0), "T1486": ("IMPACT", 9.0), "T1489": ("IMPACT", 8.5),
  "T1490": ("IMPACT", 8.5), "T1491": ("IMPACT", 8.0), "T1498": ("IMPACT", 8.0),
  "T1499": ("IMPACT", 8.0), "T1529": ("IMPACT", 9.0), "T1561": ("IMPACT", 9.0),
  "T1657": ("IMPACT", 8.0),
}

# ── Severity multipliers ──────────────────────────────────────────────────────
SEVERITY_WEIGHT_BOOST: Dict[str, float] = {
  "critical": 2.0,
  "high":     1.5,
  "medium":   1.0,
  "low":      0.6,
  "info":     0.3,
  "unknown":  1.0,
}

# ── Keyword → phase fallback (Description/Title fields) ──────────────────────
_KEYWORD_TO_PHASE: List[Tuple[List[str], str, float]] = [
  (["scan", "recon", "probe", "enumerat", "fingerprint", "osint"],
   "RECON", 1.0),
  (["phish", "brute force", "credential", "login fail", "password spray",
    "exploit", "initial access", "payload", "dropper"],
   "INITIAL_ACCESS", 3.0),
  (["malware", "script", "powershell", "command exec", "wscript", "mshta",
    "macro", "shellcode", "ransomware execut", "c2", "beacon"],
   "EXECUTION", 4.0),
  (["backdoor", "persist", "scheduled task", "registry", "startup", "cron",
    "service install", "rootkit"],
   "PERSISTENCE", 6.0),
  (["lateral", "rdp", "smb", "wmi", "pass-the-hash", "pass-the-ticket",
    "mimikatz", "kerberoast", "movement", "privilege"],
   "LATERAL_MOVEMENT", 5.0),
  (["exfil", "data leak", "upload", "mega", "ftp", "dns tunnel",
    "data transfer", "c2 upload", "steal"],
   "EXFILTRATION", 7.0),
  (["ransom", "encrypt", "wiper", "destroy", "ddos", "impact", "lock",
    "disable", "shutdown", "corrupt"],
   "IMPACT", 8.0),
]


def get_phase_enriched(alert: dict) -> Tuple[str, float]:
  """
  Enriched phase detection using all available alert fields:
    1. Category + Type  (ENISA_PHASE_MAP)
    2. Category alone   (ENISA_PHASE_MAP with empty type)
    3. MitreAttack      (MITRE_TO_PHASE)
    4. Severity boost   (SEVERITY_WEIGHT_BOOST)
    5. Description/Title keyword fallback (when still UNKNOWN)

  Returns (phase, weight) — highest confidence wins.
  Severity always boosts the winning weight.
  """
  cat   = alert.get("Category", "").lower().strip()
  atype = alert.get("Type", "").lower().strip()
  sev   = alert.get("Severity", "unknown").lower().strip()
  mitre = alert.get("MitreAttack", "").strip()
  desc  = (alert.get("Description", "") + " " + alert.get("Title", "")).lower()

  sev_mult = SEVERITY_WEIGHT_BOOST.get(sev, 1.0)

  # Step 1: Category + Type lookup
  phase1, w1 = ENISA_TO_PHASE.get((cat, atype), ("UNKNOWN", 0.0))

  # Step 1b: Category alone (empty type fallback)
  if phase1 == "UNKNOWN" and atype:
    phase1b, w1b = ENISA_TO_PHASE.get((cat, ""), ("UNKNOWN", 0.0))
    if w1b > w1:
      phase1, w1 = phase1b, w1b

  # Step 2: MitreAttack lookup
  phase2, w2 = "UNKNOWN", 0.0
  if mitre:
    import re as _re
    codes = _re.findall(r"T\d{4}(?:\.\d{3})?", mitre)
    for code in codes:
      base = code.split(".")[0]
      if base in MITRE_TO_PHASE:
        pm, wm = MITRE_TO_PHASE[base]
        if wm > w2:
          phase2, w2 = pm, wm

  # Step 3: pick best between step 1 and 2
  if w2 > w1:
    best_phase, best_w = phase2, w2
  else:
    best_phase, best_w = phase1, w1

  # Step 4: keyword fallback if still UNKNOWN
  if best_phase == "UNKNOWN" and desc.strip():
    for keywords, kphase, kw in _KEYWORD_TO_PHASE:
      if any(kw_token in desc for kw_token in keywords):
        best_phase, best_w = kphase, kw
        break

  # Step 5: apply severity multiplier
  final_weight = round(best_w * sev_mult, 2)
  return (best_phase, final_weight)


def get_phase(category: str, alert_type: str) -> Tuple[str, float]:
  """Return (phase, weight) for a category/type pair."""
  key = (category.lower().strip(), alert_type.lower().strip())
  result = ENISA_PHASE_MAP.get(key)
  if result:
    return result
  # Fallback: category alone
  key_cat = (category.lower().strip(), "")
  return ENISA_PHASE_MAP.get(key_cat, ("UNKNOWN", 0.0))


def get_phases_from_sequence(sequence: List[str]) -> List[str]:
  """Remove duplicates and UNKNOWN from a phase sequence."""
  seen = set()
  result = []
  for p in sequence:
    if p != "UNKNOWN" and p not in seen:
      seen.add(p)
      result.append(p)
  return sorted(result, key=lambda p: PHASE_PRIORITY.get(p, 99))


def generate_hypotheses(phases: List[str]) -> List[Tuple[str, float]]:
  """Generate CISO hypotheses from detected phases using SEQUENCE_TO_CISO."""
  if not phases:
    return [
      ("Malware Infrastructure & Botnet Activity", 0.50),
      ("Reconnaissance & Pre-Attack Intelligence Gathering", 0.30),
      ("Others", 0.20),
    ]

  
  # Ordenar canonicamente por kill-chain antes do lookup
  unique = list(dict.fromkeys(p for p in phases if p != "UNKNOWN"))
  unique_sorted = sorted(unique, key=lambda p: PHASE_PRIORITY.get(p, 99))
  phases_tuple = tuple(unique_sorted)

  # Exact match
  if phases_tuple in SEQUENCE_TO_CISO:
    return SEQUENCE_TO_CISO[phases_tuple][:3]

  # Longest prefix match
  for i in range(len(phases_tuple) - 1, 0, -1):
    prefix = phases_tuple[:i]
    if prefix in SEQUENCE_TO_CISO:
      return SEQUENCE_TO_CISO[prefix][:3]

  # Single phase match (any phase in the sequence)
  for phase in phases_tuple:
    single = (phase,)
    if single in SEQUENCE_TO_CISO:
      return SEQUENCE_TO_CISO[single][:3]

  # Final fallback based on highest-weight phase
  best = max(phases_tuple, key=lambda p: PHASE_WEIGHTS.get(p, 0), default="")
  if best == "IMPACT":
    return [
      ("Ransomware & Digital Extortion",          0.70),
      ("Destructive Operations & Wipeware",       0.20),
      ("Others",                                  0.10),
    ]
  if best == "EXFILTRATION":
    return [
      ("Data Exfiltration & Corporate Espionage", 0.70),
      ("Advanced Persistent Threats (APT)",       0.20),
      ("Others",                                  0.10),
    ]
  return [
    ("Advanced Persistent Threats (APT)",         0.50),
    ("Malware Infrastructure & Botnet Activity",  0.30),
    ("Others",                                    0.20),
  ]


def calculate_phase_score(phases: List[str]) -> int:
  """Calculate total score from phase weights."""
  return sum(PHASE_WEIGHTS.get(p, 0) for p in phases)


def get_ciso_category_name(ciso_id: int) -> str:
  """Return canonical name for a CISO category ID."""
  return CISO_CATEGORIES.get(ciso_id, {}).get("name", f"CISO-{ciso_id}")


def get_ciso_risk_tier(ciso_id: int) -> str:
  """Return risk tier for a CISO category ID."""
  return CISO_CATEGORIES.get(ciso_id, {}).get("risk_tier", "—")


def get_ciso_label(name: str) -> str:
  """
  Return 'SHORTCODE  Full Name' for display.
  e.g. 'CRITICAL_RANSOMWARE  Ransomware & Digital Extortion'
  """
  for cat in CISO_CATEGORIES.values():
    if cat.get("name") == name:
      sc = cat.get("shortcode", "")
      return f"{sc}  {name}" if sc else name
  return name


def get_ciso_id_by_name(category_name: str) -> int:
  """Return CISO category ID for a given name string."""
  if not category_name:
    return 16

  # Direct map for common variants
  _direct: Dict[str, int] = {
    "Ransomware & Digital Extortion":                    1,
    "Destructive Operations & Wipeware":                 2,
    "Data Exfiltration & Corporate Espionage":           3,
    "Credential & Identity Compromise":                  4,
    "Advanced Persistent Threats (APT)":                 5,
    "Supply Chain & Third-Party Compromise":             6,
    "Critical Service Disruption — DDoS":                7,
    "Social Engineering, Phishing & BEC":                8,
    "System & Application Vulnerability Exploitation":   9,
    "Information Manipulation & Integrity Attacks":     10,
    "Insider Threats & Physical Security Breaches":     11,
    "Regulatory & Compliance Violations":               12,
    "Cryptojacking & Unauthorized Resource Abuse":      13,
    "Malware Infrastructure & Botnet Activity":         14,
    "Reconnaissance & Pre-Attack Intelligence Gathering": 15,
    "Others":                                           16,
    "Other":                                            16,
    "Operational Noise":                                16,
    # Legacy/informal labels that may appear in old persisted state
    "Major Breach with Impact":                          1,
    "Major Breach":                                      1,
    "Critical Combined Attack":                          1,
    "Critical Breach":                                   1,
    "Critical Incident":                                 1,
    "Critical Security Incident":                        1,
    "Ransomware Attack":                                 1,
    "APT Data Theft":                                    3,
    "Data Breach":                                       3,
    "Major Data Breach":                                 3,
    "APT Exfiltration":                                  3,
    "Persistent Exfiltration":                           3,
    "APT Persistence":                                   5,
    "Complex APT Intrusion":                             5,
    "Sophisticated APT":                                 5,
    "APT Activity":                                      5,
    "APT Campaign":                                      5,
    "Advanced APT":                                      5,
    "Targeted Intrusion Campaign":                       5,
    "Active Intrusion":                                  5,
    "Targeted Attack":                                   5,
    "Complex Intrusion":                                 5,
    "Malware Deployment":                                14,
    "System Compromise":                                 14,
    "Advanced Malware":                                  14,
    "Lateral Movement with Malware":                     14,
    "Destructive Lateral Movement":                      2,
    "Destructive Malware":                               2,
    "Destructive Exfiltration":                          2,
    "APT Destructive Attack":                            2,
    "Persistent Threat":                                 5,
    "Ransomware Propagation":                            1,
    "Critical Impact":                                   1,
    "Severe Incident":                                   1,
    "Major Security Incident":                           1,
    "Coordinated Attack":                                1,
  }

  if category_name in _direct:
    return _direct[category_name]

  # Exact match by name or shortcode
  for ciso_id, cat_info in CISO_CATEGORIES.items():
    if cat_info.get("name") == category_name or cat_info.get("shortcode") == category_name:
      return ciso_id

  # Keyword fallback
  lower = category_name.lower()
  _kw: Dict[str, int] = {
    "ransomware": 1, "ransom": 1, "lockbit": 1, "extort": 1, "encrypt": 1,
    "wiper": 2, "destructive": 2, "wipeware": 2, "sabotage": 2,
    "exfiltration": 3, "data leak": 3, "data breach": 3, "espionage": 3,
    "credential": 4, "identity": 4, "brute force": 4, "mimikatz": 4,
    "apt": 5, "nation-state": 5, "fileless": 5, "persistent threat": 5,
    "supply chain": 6, "third-party": 6, "vendor": 6,
    "ddos": 7, "denial of service": 7, "flood": 7,
    "phishing": 8, "bec": 8, "social engineering": 8,
    "vulnerability": 9, "exploit": 9, "zero-day": 9, "cve": 9,
    "integrity": 10, "manipulation": 10, "defacement": 10,
    "insider": 11, "physical": 11,
    "compliance": 12, "regulatory": 12, "gdpr": 12, "nis2": 12,
    "cryptojacking": 13, "cryptominer": 13, "mining": 13,
    "botnet": 14, "c2": 14, "beacon": 14, "malware": 14,
    "recon": 15, "scanning": 15, "osint": 15,
  }
  for kw, cid in _kw.items():
    if kw in lower:
      return cid

  return 16


_mappings_logger.info("Mappings module loaded with complete CISO/ENISA taxonomy")