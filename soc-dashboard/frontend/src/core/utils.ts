// File: soc-dashboard/frontend/src/core/utils.ts

export function esc(s: string): string {
if (!s) return '';
return s
.replace(/&/g, '&amp;')
.replace(/</g, '&lt;')
.replace(/>/g, '&gt;')
.replace(/"/g, '&quot;');
}

export function fmtDay(ms: number): string {
const d = new Date(ms);
return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function fmtTs(ms: number): string {
if (!ms) return '—';
// Alterado para mostrar até segundos (YYYY-MM-DD HH:MM:SS)
return new Date(ms).toISOString().replace('T', ' ').replace('Z', '').slice(0, 19);
}

export function fmtTimeShort(ms: number): string {
if (!ms) return '—';
// Já mostra HH:MM (sem segundos) - mantido
return new Date(ms).toISOString().slice(11, 16);
}

// NOVO: timestamp com segundos para exibição no header
export function fmtTimestampSeconds(ms: number): string {
if (!ms) return '—';
const d = new Date(ms);
return d.toLocaleString('pt-PT', {
 day: '2-digit',
 month: '2-digit',
 year: 'numeric',
 hour: '2-digit',
 minute: '2-digit',
 second: '2-digit'
});
}

export function fmtDateTime(ms: number): string {
if (!ms) return '—';
return new Date(ms).toISOString().replace('T', ' ').replace('Z', '').slice(0, 19);
}

export function clamp(v: number, lo: number, hi: number): number {
return Math.max(lo, Math.min(hi, v));
}

export function scoreToState(score: number): string {
if (score <= 2) return 'RUIDO_OPERACIONAL';
if (score <= 5) return 'ATIVIDADE_SUSPEITA';
if (score <= 9) return 'INCIDENTE_SEGURANCA';
if (score <= 14) return 'INCIDENTE_GRAVE';
return 'CRITICAL_COMBINED_ATTACK';
}

export function msToTrackPct(ms: number, dataMinMs: number, dataMaxMs: number): number {
const span = dataMaxMs - dataMinMs || 1;
return Math.max(0, Math.min(100, ((ms - dataMinMs) / span) * 100));
}

export function trackPctToMs(pct: number, dataMinMs: number, dataMaxMs: number): number {
const span = dataMaxMs - dataMinMs || 1;
return dataMinMs + (pct / 100) * span;
}

export function isSevereTier(tier: string): boolean {
const SEVERE_TIERS = new Set(['CRITICAL', 'HIGH', 'MEDIUM-HIGH']);
return SEVERE_TIERS.has(tier);
}

export function getReferenceTimeMs(dataMaxMs: number): number {
const now = Date.now();
return Math.min(now, dataMaxMs);
}

export function formatTimeAgo(ms: number): string {
const diff = Date.now() - ms;
const minutes = Math.floor(diff / 60000);
const hours = Math.floor(diff / 3600000);
const days = Math.floor(diff / 86400000);

if (days > 0) return `${days}d ago`;
if (hours > 0) return `${hours}h ago`;
if (minutes > 0) return `${minutes}m ago`;
return `${Math.floor(diff / 1000)}s ago`;
}

export function msToTimeStr(ms: number): string {
if (!ms) return '—';
return new Date(ms).toLocaleTimeString().slice(0, 5);
}

export function fmtDateTimeSeconds(ms: number): string {
 if (!ms) return '—';
 const d = new Date(ms);
 return d.toLocaleString('pt-PT', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit'
 });
}

