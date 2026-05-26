import { PHASE_COLORS, PHASE_ABBRS } from '../core/constants';

export interface TimelineAlert {
  number: string;
  timestamp_ms: number;
  category: string;
  type: string;
  phase?: string;
  severity?: string;
  window_id?: string;
  is_noise?: boolean;
}

function esc(s: string): string {
return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function fmtSec(ms: number): string {
const d = new Date(ms);
const hh = d.getHours().toString().padStart(2,'0');
const mm = d.getMinutes().toString().padStart(2,'0');
const ss = d.getSeconds().toString().padStart(2,'0');
return `${hh}:${mm}:${ss}`;
}

function alertColor(a: TimelineAlert): string {
  if (a.is_noise) return '#475569';  
  if (a.phase && PHASE_COLORS[a.phase]) return PHASE_COLORS[a.phase];
  if (a.severity === 'critical') return '#dc2626';
  if (a.severity === 'high')     return '#ea580c';
  if (a.severity === 'medium')   return '#d97706';
  return '#38bdf8';
}

function severityRing(severity?: string): string {
if (severity === 'critical') return '#dc2626';
if (severity === 'high')     return '#ea580c';
if (severity === 'medium')   return '#d97706';
return 'rgba(255,255,255,.6)';
}

function pinLabel(a: TimelineAlert): string {
  if (a.is_noise) return 'NS';
  if (a.phase && PHASE_ABBRS[a.phase]) return PHASE_ABBRS[a.phase];
  const c = a.category || a.type || '';
  return c.slice(0,2).toUpperCase() || 'AL';
}

/**
* Calcula a largura necessária do SVG baseado no número de alertas
*/
function calculateSVGWidth(alertCount: number): number {
const PIN_GAP = 72;
const PAD_LEFT = 20;
const PAD_RIGHT = 48;
return PAD_LEFT + (alertCount - 1) * PIN_GAP + PAD_RIGHT;
}

/**
* Kibana-style timeline SVG.
*/
export interface AlertTimelineOptions {
alerts: TimelineAlert[];
height?: number;
onAlertClick?: (alert: TimelineAlert) => void;
selectedAlertNumber?: string;
}

export function renderAlertTimelineSVG(opts: AlertTimelineOptions): string {
const { alerts, height = 140, onAlertClick, selectedAlertNumber } = opts;

if (!alerts || alerts.length === 0) {
 return `<div class="timeline-empty-state">
 <div class="empty-icon">📡</div>
 <div>Aguardando alertas...</div>
 </div>`;
}

const sorted = [...alerts].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
const n = sorted.length;

const PIN_GAP    = 72;
const PAD_LEFT   = 20;
const PAD_RIGHT  = 48;
const PIN_Y      = 32;
const AXIS_Y     = height - 18;
const LABEL_Y    = height - 4;
const BAR_MAX_H  = 16;
const BAR_Y_BASE = PIN_Y + 14;

const svgW = calculateSVGWidth(n);

const gaps: number[] = sorted.map((a, i) =>
 i === 0 ? 0 : a.timestamp_ms - sorted[i-1].timestamp_ms
);
const maxGap = Math.max(1, ...gaps);

let barsSvg = '';
for (let i = 1; i < n; i++) {
 const x0  = PAD_LEFT + (i-1) * PIN_GAP;
 const x1  = PAD_LEFT + i * PIN_GAP;
 const xm  = (x0 + x1) / 2;
 const bh  = Math.max(3, (gaps[i] / maxGap) * BAR_MAX_H);
 const col = gaps[i] > maxGap * 0.7 ? '#f97316'
   : gaps[i] > maxGap * 0.4 ? '#fbbf24' : '#38bdf822';
 barsSvg += `<rect x="${x0+4}" y="${BAR_Y_BASE}" width="${PIN_GAP-8}" height="${bh}"
 fill="${col}" fill-opacity="0.25" rx="2"/>`;
 const gapSec = Math.round(gaps[i] / 1000);
 if (gapSec > 0) {
 barsSvg += `<text x="${xm}" y="${BAR_Y_BASE + bh + 9}"
  text-anchor="middle" font-family="'IBM Plex Mono',monospace"
  font-size="7" fill="#64748b">+${gapSec}s</text>`;
 }
}

const axisLine = `<line x1="${PAD_LEFT}" y1="${AXIS_Y}"
 x2="${svgW - PAD_RIGHT + 20}" y2="${AXIS_Y}"
 stroke="rgba(148,163,184,.3)" stroke-width="1"/>`;

let connector = '';
for (let i = 0; i < n - 1; i++) {
 const x1  = PAD_LEFT + i * PIN_GAP;
 const x2  = PAD_LEFT + (i + 1) * PIN_GAP;
 const col = alertColor(sorted[i]);
 connector += `<line x1="${x1}" y1="${PIN_Y}" x2="${x2}" y2="${PIN_Y}"
 stroke="${col}" stroke-width="1.5" stroke-opacity=".5"/>`;
}

let pinsSvg = '';
for (let i = 0; i < n; i++) {
 const a    = sorted[i];
 const x    = PAD_LEFT + i * PIN_GAP;
 const col  = alertColor(a);
 const ring = severityRing(a.severity);
 const lbl  = pinLabel(a);
 const sel  = selectedAlertNumber === a.number;
 const r    = sel ? 15 : 11;
 const ts   = fmtSec(a.timestamp_ms);
 const onclick = onAlertClick
 ? `onclick="window._onTimelineAlertClick&&window._onTimelineAlertClick('${esc(a.number)}')" style="cursor:pointer"`
 : '';

 const glow = sel
 ? `<circle cx="${x}" cy="${PIN_Y}" r="${r+5}" fill="${col}" fill-opacity=".15"/>`
 : '';

 const isNoise = a.is_noise === true;
 const groupAttr = isNoise ? `opacity="0.4"` : '';

 pinsSvg += `
 <g class="tl-pin" data-n="${esc(a.number)}" ${onclick} ${groupAttr}>
  ${glow}
  <circle cx="${x}" cy="${PIN_Y}" r="${r+3}" fill="${col}" fill-opacity=".12"/>
  <circle cx="${x}" cy="${PIN_Y}" r="${r}"
  fill="${col}" stroke="${ring}" stroke-width="2"/>
  <text x="${x}" y="${PIN_Y+4}" text-anchor="middle"
  font-family="'IBM Plex Mono',monospace" font-size="8" font-weight="700"
  fill="#0f172a" style="pointer-events:none">${esc(lbl)}</text>
  <text x="${x}" y="${PIN_Y - r - 5}" text-anchor="middle"
  font-family="'IBM Plex Mono',monospace" font-size="8" fill="${col}"
  style="pointer-events:none">${esc(a.number)}</text>
  <text x="${x}" y="${LABEL_Y}" text-anchor="middle"
  font-family="'IBM Plex Mono',monospace" font-size="8" fill="rgba(148,163,184,.8)"
  style="pointer-events:none">${esc(ts)}</text>
  <title>${esc(a.number)} | ${esc(a.category)}/${esc(a.type)} | ${esc(ts)} | ${esc(a.phase||'—')}</title>
 </g>`;
}

const nowX = PAD_LEFT + (n-1) * PIN_GAP + 24;
const nowMarker = `
 <line x1="${nowX}" y1="${PIN_Y - 18}" x2="${nowX}" y2="${AXIS_Y}"
 stroke="#22c55e" stroke-width="1.5" stroke-dasharray="4,3"/>
 <text x="${nowX + 4}" y="${PIN_Y - 8}" font-family="'IBM Plex Mono',monospace"
 font-size="8" font-weight="700" fill="#22c55e">NOW</text>`;

// Wrap SVG em div que permite scroll
return `<div class="timeline-scroll-inner" style="display: inline-block; min-width: 100%;">
 <svg width="${svgW}" height="${height}"
 style="display:block;background:var(--bg2);border-radius:6px;">
 ${barsSvg}
 ${connector}
 ${axisLine}
 ${pinsSvg}
 ${nowMarker}
 </svg>
</div>`;
}

export function setupTimelineClickHandler(onClick: (n: string) => void): void {
(window as any)._onTimelineAlertClick = onClick;
}

// ========== FUNÇÕES CORRIGIDAS PARA SCROLL ==========

let scrollContainer: HTMLElement | null = null;
let resizeObserver: ResizeObserver | null = null;
let autoScrollEnabled = true;

/**
* Configura o container de scroll com observers para resize e mudanças
*/
export function setupTimelineScroll(containerId: string = 'timeline-content'): void {
scrollContainer = document.getElementById(containerId);

if (!scrollContainer) {
 console.warn('Scroll container not found:', containerId);
 return;
}

// Força o container a ter scroll horizontal visível
scrollContainer.style.overflowX = 'scroll';
scrollContainer.style.overflowY = 'hidden';

// Configura observer para mudanças de tamanho (redimensionamento da janela)
if (resizeObserver) {
 resizeObserver.disconnect();
}

resizeObserver = new ResizeObserver(() => {
 if (autoScrollEnabled) {
 scrollToEndInstant();
 }
 // Força a barra de scroll a ser visível
 forceScrollbarVisibility();
});

resizeObserver.observe(scrollContainer);

// Observer para detectar mudanças no conteúdo
const mutationObserver = new MutationObserver(() => {
 if (autoScrollEnabled) {
 scrollToEndInstant();
 }
});

mutationObserver.observe(scrollContainer, {
 childList: true,
 subtree: true,
 attributes: true,
 attributeFilter: ['style', 'class']
});

// Scroll inicial e força visibilidade da barra
setTimeout(() => {
 scrollToEndInstant();
 forceScrollbarVisibility();
}, 100);

// Listener para redimensionamento da janela
window.addEventListener('resize', () => {
 setTimeout(() => {
 if (autoScrollEnabled) {
  scrollToEndInstant();
 }
 forceScrollbarVisibility();
 }, 50);
});
}

/**
* Força a barra de scroll a ser visível
*/
function forceScrollbarVisibility(): void {
if (!scrollContainer) return;

// Verifica se há overflow
const hasOverflow = scrollContainer.scrollWidth > scrollContainer.clientWidth;

if (hasOverflow) {
 scrollContainer.style.overflowX = 'scroll';
} else {
 // Se não há overflow, ainda assim mantém scroll para quando houver
 scrollContainer.style.overflowX = 'auto';
}
}

/**
* Scroll suave para o final
*/
export function scrollToEnd(): void {
if (!scrollContainer) return;

autoScrollEnabled = true;
scrollContainer.scrollTo({
 left: scrollContainer.scrollWidth,
 behavior: 'smooth'
});

// Garante que a barra de scroll aparece
setTimeout(() => forceScrollbarVisibility(), 100);
}

/**
* Scroll imediato sem animação
*/
export function scrollToEndInstant(): void {
if (!scrollContainer) return;

autoScrollEnabled = true;
scrollContainer.scrollLeft = scrollContainer.scrollWidth;
forceScrollbarVisibility();
}

