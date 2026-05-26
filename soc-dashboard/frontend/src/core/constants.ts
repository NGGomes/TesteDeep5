export const PHASE_COLORS: Record<string, string> = {
RECON: '#38bdf8',
INITIAL_ACCESS: '#bef264',
EXECUTION: '#f97316',
LATERAL_MOVEMENT: '#e879f9',
PERSISTENCE: '#67e9f9',
EXFILTRATION: '#f472b6',
IMPACT: '#ef4444',
};

export const PHASE_ABBRS: Record<string, string> = {
RECON: 'Re',
INITIAL_ACCESS: 'In',
EXECUTION: 'Ex',
LATERAL_MOVEMENT: 'La',
PERSISTENCE: 'Pe',
EXFILTRATION: 'Ef',
IMPACT: 'Ac',
};

export const PHASE_WEIGHT: Record<string, number> = {
'RECON': 1,
'INITIAL_ACCESS': 3,
'EXECUTION': 4,
'PERSISTENCE': 6,
'LATERAL_MOVEMENT': 5,
'EXFILTRATION': 7,
'IMPACT': 8,
};

export type RiskTier = 'CRITICAL' | 'HIGH' | 'MEDIUM-HIGH' | 'MEDIUM' | 'LOW-MED' | 'LOW' | '—';

export const TIER_ORDER: Record<RiskTier, number> = {
'CRITICAL': 0,
'HIGH': 1,
'MEDIUM-HIGH': 2,
'MEDIUM': 3,
'LOW-MED': 4,
'LOW': 5,
'—': 6,
};

export const CISO_STATE_LABEL: Record<string, string> = {
'CRITICAL_COMBINED_ATTACK': 'Critical Combined Attack',
'INCIDENTE_GRAVE': 'Serious Incident',
'INCIDENTE_SEGURANCA': 'Security Incident',
'ATIVIDADE_SUSPEITA': 'Suspicious Activity',
'RUIDO_OPERACIONAL': 'Operational Noise',
};

export const MITRE_LABELS: Record<string, string> = {
'T1486': 'Data Encrypted for Impact',
'T1059': 'Command & Scripting Interpreter',
'T1568': 'Dynamic Resolution',
'T1566': 'Phishing',
'T1078': 'Valid Accounts',
'T1190': 'Exploit Public-Facing App',
'T1021': 'Remote Services',
'T1003': 'OS Credential Dumping',
'T1055': 'Process Injection',
'T1071': 'App Layer Protocol (C2)',
'T1082': 'System Information Discovery',
'T1041': 'Exfiltration Over C2',
'T1489': 'Service Stop',
'T1036': 'Masquerading',
'T1547': 'Boot/Logon Autostart',
'T1498': 'Network Denial of Service',
'T1195': 'Supply Chain Compromise',
'T1110': 'Brute Force',
'T1496': 'Resource Hijacking',
'T1595': 'Active Scanning',
'T1565': 'Data Manipulation',
};

export const STORAGE_KEYS = {
ALERTS: 'ciso_alerts',
TRIGGER_META: 'ciso_trigger_meta',
AGENT2_REPORTS: 'ciso_agent2_reports',
SLICE: 'ciso_slice',
SELECTED_HYP: 'ciso_selected_hyp',
TIMELINE_MONTH: 'ciso_timeline_month',
TOTAL_RECEIVED: 'ciso_total_received',
CONNECTION: 'ciso_connection',
WINDOWS: 'ciso_windows',
HYPOTHESES: 'ciso_hypotheses',
GRAPH_STATE: 'ciso_graph_state',
ACTIVE_WINDOWS: 'ciso_active_windows',
} as const;

export const DEFAULT_ACTIVE_WINDOW_MINUTES = 15;

export const CATEGORY_BADGE_MAP: Record<string, {icon: string, short: string}> = {
    "Ransomware & Digital Extortion": { icon: "🔴", short: "Ransomware" },
    "Data Exfiltration & Corporate Espionage": { icon: "🟠", short: "Exfiltration" },
    "Advanced Persistent Threats (APT)": { icon: "🟡", short: "APT" },
    "Credential & Identity Compromise": { icon: "🔵", short: "Credential" },
    "Destructive Operations & Wipeware": { icon: "💀", short: "Destructive" },
    "Supply Chain & Third-Party Compromise": { icon: "📦", short: "Supply Chain" },
    "Critical Service Disruption — DDoS": { icon: "🌊", short: "DDoS" },
    "Social Engineering, Phishing & BEC": { icon: "🎣", short: "Phishing" },
    "System & Application Vulnerability Exploitation": { icon: "🐛", short: "Exploit" },
    "Insider Threats & Physical Security Breaches": { icon: "👤", short: "Insider" },
    "Regulatory & Compliance Violations": { icon: "⚖️", short: "Compliance" },
    "Reconnaissance & Pre-Attack Intelligence Gathering": { icon: "🔍", short: "Recon" },
    "Operational Noise": { icon: "📡", short: "Noise" },
    "Other": { icon: "❓", short: "Other" },
    "Major Breach": { icon: "🔴", short: "Major Breach" },
    "Major Breach with Impact": { icon: "🔴", short: "Major Breach" },
    "Critical Combined Attack": { icon: "🔴", short: "Critical" },
};

// core/constants.ts

export function getCategoryBadge(categoryName: string): string {
    if (!categoryName) return "⚠️ Unknown";
    
    // 1. Match exato
    const exactMatch = CATEGORY_BADGE_MAP[categoryName];
    if (exactMatch) return `${exactMatch.icon} ${exactMatch.short}`;
    
    // 2. Match por palavra-chave (fuzzy)
    const lowerName = categoryName.toLowerCase();
    
    if (lowerName.includes("ransomware") || lowerName.includes("ransom")) {
        return "🔴 Ransomware";
    }
    if (lowerName.includes("exfiltration") || lowerName.includes("data leak") || lowerName.includes("data breach")) {
        return "🟠 Exfiltration";
    }
    if (lowerName.includes("apt") || lowerName.includes("advanced persistent")) {
        return "🟡 APT";
    }
    if (lowerName.includes("credential") || lowerName.includes("identity")) {
        return "🔵 Credential";
    }
    if (lowerName.includes("destructive") || lowerName.includes("wiper") || lowerName.includes("wipeware")) {
        return "💀 Destructive";
    }
    if (lowerName.includes("supply chain") || lowerName.includes("third-party")) {
        return "📦 Supply Chain";
    }
    if (lowerName.includes("ddos") || lowerName.includes("disruption")) {
        return "🌊 DDoS";
    }
    if (lowerName.includes("phishing") || lowerName.includes("bec") || lowerName.includes("social engineering")) {
        return "🎣 Phishing";
    }
    if (lowerName.includes("vulnerability") || lowerName.includes("exploit") || lowerName.includes("cve")) {
        return "🐛 Exploit";
    }
    if (lowerName.includes("insider") || lowerName.includes("privileged")) {
        return "👤 Insider";
    }
    if (lowerName.includes("compliance") || lowerName.includes("regulatory") || lowerName.includes("nis2") || lowerName.includes("gdpr")) {
        return "⚖️ Compliance";
    }
    if (lowerName.includes("recon") || lowerName.includes("reconnaissance") || lowerName.includes("scanning")) {
        return "🔍 Recon";
    }
    if (lowerName.includes("major breach") || lowerName.includes("critical combined")) {
        return "🔴 Major Breach";
    }
    
    // 3. Fallback: primeiras 2 palavras
    const words = categoryName.split(' ').slice(0, 2).join(' ');
    return words.slice(0, 15) || categoryName.slice(0, 15);
}
