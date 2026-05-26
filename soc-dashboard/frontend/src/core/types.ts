import type { RiskTier } from './constants';
export type { RiskTier };

export interface WindowHypothesis {
windowId: string;
hypothesisLabel: string;
probability: number;
phaseScore: number;
phases: string[];
createdAt: number;
expiresAt: number;
alerts: AlertPayload[];
isClosed: boolean;
closeReason?: 'timeout' | 'validation' | 'convergence';
isConfirmed: boolean;
confirmedAt?: number;
}

export interface CISOClassification {
ciso_category_id: number;
ciso_category_name: string;
risk_tier: RiskTier;
plausibility: number;
mitre_technique?: string;
}

export interface AlertPayload {
number: string;
title: string;
severity: string;
category: string;
ts: string;
source: string;
affected_asset?: string;
mitre?: string;
kill_chain?: string;
mitre_detail?: { tech: string; name: string; tactic: string; mitigation: string };
classifications: CISOClassification[];
primary_ciso: CISOClassification;
soc_routing?: string;
tlp?: string;
tags?: string;
emitted_at: string;
detected_threat_type?: string;
ciso_state?: string;
phase_score?: number;
phases_detected?: string[];
trigger_type?: string;
discard_reason?: string;
is_discarded?: boolean;
window_id?: string;
is_noise?: boolean;
timestamp_ms?: number;
}

export interface IncidentHypothesis {
id: string;
windowStart: number;
windowEnd: number;
tier: RiskTier;
category: string;
mitreTechs: string[];
evidenceCount: number;
evidenceGap: number;
isSevere: boolean;
enisaDecision: string;
sources: string[];
killChains: number;
execAction: string;
nis2: string;
gdpr: string;
alerts: AlertPayload[];
anomalyScore: number;
reportText: string;
detectedThreatType: string;
cisoState: string;
phaseScore: number;
phasesDetected: string[];
triggerTypes: string[];
discardedCount: number;
discardReasons: string[];
windowId?: string;
expiresAt?: number;
isClosed?: boolean;
}

export interface MITRECoMatrix {
techs: string[];
matrix: number[][];
}

export interface SliceState {
dataMinMs: number;
dataMaxMs: number;
windowStartMs: number;
windowEndMs: number;
}

export interface TriggerMeta {
ciso_state: string;
phase_score: number;
phases_detected: string[];
trigger_type: string;
}

export interface Agent2Report {
metadata: {
window_id?: string;
window_start?: number;
window_end?: number;
window_start_ms?: number;
window_end_ms?: number;
output_timestamp?: string;
generated_at?: string;
source_report?: string;
tex_file?: string;
pdf_file?: string;
llm_used?: boolean;
selected_hypothesis?: string;
confirmation_method?: string;
confirmed?: boolean;
model_used?: string;
alert_count?: number;
phases?: string[];
phase_score?: number;
};
ciso_report?: {
top_risk_tier?: string;
executive_summary?: string;
summary?: string;
top_categories?: Array<[string, number]>;
business_impact?: string;
regulatory_implications?: string;
strategic_recommendations?: string[];
primary_probability?: number;
primary_hypothesis?: string;
};
soc_report?: {
detected_cves?: string[];
affected_assets?: string[];
total_alerts?: number;
mitre_techniques?: string[];
kill_chain_phases?: string[];
remediation_steps?: string[];
timeline?: Array<{ timestamp: string; event: string }>;
ioc_bundle?: {
ipv4_addresses?: string[];
fqdns?: string[];
cve_ids?: string[];
hashes?: string[];
executables?: string[];
};
raw_alerts?: unknown[];
trigger_events?: Array<{ timestamp: string; id: string; category: string; tier: string; kill_chain: string }>;
};
decision?: {
selected_hypothesis?: { label: string; probability: number; risk_tier?: string };
decision_method?: string;
all_hypotheses?: Array<{ label: string; probability: number }>;
};
// Flat label list for badge matching
confirmed_hypothesis_labels?: string[];
// Object list with full detail
confirmed_hypotheses?: Array<{
label: string;
confidence: number;
confidence_percent: number;
risk_tier: string;
confirmed_by: string;
confirmed_at: string;
}>;
executive_summary?: string;
recommended_actions?: string[];
regulatory_impact?: Record<string, string>;
}

export interface WindowState {
window_id: string;
created_at_ms: number;
expires_at_ms: number;
alert_count: number;
phases: string[];
phase_score: number;
is_closed: boolean;
close_reason?: string;
current_ciso_options: Array<{
category: string;
probability: number;
risk_tier: string;
}>;
alerts: AlertPayload[];
}

export interface HypothesisGraphNode {
label: string;
cumulative_score: number;
evidence_count: number;
confirmed: boolean;
confirmation_time_ms: number;
risk_tier: string;
}

export interface HypothesisGraphEdge {
source: string;
target: string;
weight: number;
evidence_count: number;
}

export interface HypothesisGraphState {
nodes: HypothesisGraphNode[];
edges: HypothesisGraphEdge[];
confirmed_hypotheses: string[];
kill_chain_progress: Record<string, number>;
total_evidence_windows: number;
}
