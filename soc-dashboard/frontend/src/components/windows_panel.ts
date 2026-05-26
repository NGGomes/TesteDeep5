import './windows_panel.css';
import type { WindowState, AlertPayload } from '../core/types';
import { esc } from '../core/utils';
import { PHASE_COLORS, PHASE_ABBRS, getCategoryBadge } from '../core/constants';

// ── Score filter state ────────────────────────────────────────────────────────
let _minScore: number = (() => {
 const v = sessionStorage.getItem('wm_min_score');
 return v !== null ? parseInt(v, 10) : 0;
})();

// ── Risk filter state ────────────────────────────────────────────────────────
// MOVER PARA O ESCOPO GLOBAL (fora do requestAnimationFrame)
let _riskFilter: Set<string> = (() => {
 try {
  const saved = sessionStorage.getItem('wm_risk');
  return saved ? new Set<string>(JSON.parse(saved)) : new Set<string>();
 } catch { return new Set<string>(); }
})();

function _saveRiskFilter(): void {
 sessionStorage.setItem('wm_risk', JSON.stringify([..._riskFilter]));
}

// ── Window mode state ─────────────────────────────────────────────────────────
let _windowMode: 'adaptive' | 'fixed' = 'fixed';

function _applyWindowModeToButton(btn: HTMLButtonElement, mode: 'adaptive' | 'fixed') {
 btn.dataset.mode = mode;
 btn.textContent  = mode === 'adaptive' ? '⚡ adaptive' : '📐 fixed';
 btn.classList.toggle('wm-mode-adaptive', mode === 'adaptive');
}

function _setMinScore(val: number): void {
 _minScore = val;
 sessionStorage.setItem('wm_min_score', String(val));
}

(window as any).__wmSetMinScore = (val: number) => {
 _setMinScore(val);
 (window as any).__wmMinScore = val;
 const el = document.getElementById('wm-score-display');
 if (el) el.textContent = String(val);
 window.dispatchEvent(new CustomEvent('wm-filter-change', { detail: { minScore: val } }));
};
(window as any).__wmMinScore = _minScore;

// requestAnimationFrame (agora sem as declarações de _riskFilter)
requestAnimationFrame(async () => {
 const el = document.getElementById('wm-score-display');
 if (el) el.textContent = String(_minScore);

 // Restore risk buttons (agora _riskFilter existe globalmente)
 _riskFilter.forEach(tier => {
  const btn = document.querySelector(`.wm-risk-btn[data-tier="${tier}"]`);
  if (btn) btn.classList.add('active');
 });

 // FIX: GET /api/agent1/window-mode
 try {
  const res  = await fetch('/api/agent1/window-mode');
  const data = await res.json();
  _windowMode = data.mode === 'adaptive' ? 'adaptive' : 'fixed';
 } catch {
  _windowMode = 'fixed';
 }

 const modeBtn = document.querySelector('.wm-mode-btn') as HTMLButtonElement | null;
 if (modeBtn) _applyWindowModeToButton(modeBtn, _windowMode);
});

// Window mode toggle
(window as any).__wmToggleMode = async (btn: HTMLButtonElement) => {
 const next: 'adaptive' | 'fixed' =
  (_windowMode === 'adaptive') ? 'fixed' : 'adaptive';

 _windowMode = next;
 _applyWindowModeToButton(btn, next);

 try {
  await fetch('/api/agent1/window-mode', {
   method: 'POST',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({ mode: next }),
  });
 } catch (e) {
  console.warn('[WindowMode] Failed to set mode:', e);
 }
};

// ── Extension push ────────────────────────────────────────────────────────────
(window as any).__wmPushAlertToExtension = (el: HTMLElement) => {
 const d = el.dataset;
 window.postMessage({
  type:        'REDSHIFT_WINDOW_CONTEXT',
  windowId:    d.pushWindowid || '',
  label:       d.pushCategory || '',
  probability: 0, tier: '',
  cves: [], iocs: [], phases: [], assets: [],
  siemAlert: {
   'rule.name':  d.pushCategory || '',
   'alert_id':   d.pushNumber || '',
   'kill_chain': d.pushKillchain || '',
   'severity':   d.pushSeverity || '',
   'timestamp':  d.pushTs || '',
   'source':     'SOC Dashboard — trigger alert',
  },
 }, '*');
};

// ── Confirm hypothesis ────────────────────────────────────────────────────────
(window as any).__wmConfirmHypothesis = async (windowId: string, label: string) => {
 try {
  const res = await fetch('/api/agent1/confirm-hypothesis', {
   method: 'POST',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({ window_id: windowId, hypothesis_label: label }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (data.ok === false) {
   console.warn('[WindowsPanel] Confirm rejected by server:', data.message);
  }
  window.dispatchEvent(new CustomEvent('wm-operator-confirmed', {
   detail: { windowId, label }
  }));
 } catch (e) {
  console.error('[WindowsPanel] Confirm failed:', e);
 }
};

// ── Sort state ────────────────────────────────────────────────────────────────
type SortMode = 'score' | 'time';
let _sortMode: SortMode = (sessionStorage.getItem('wm_sort') as SortMode) || 'score';

function _setSortMode(mode: SortMode): void {
 _sortMode = mode;
 sessionStorage.setItem('wm_sort', mode);
}

const _TIER_ORDER: Record<string, number> = {
 'CRITICAL': 0, 'HIGH': 1, 'MEDIUM-HIGH': 2,
 'MEDIUM': 3, 'LOW-MED': 4, 'LOW': 5, '—': 6,
};

function _windowTopTier(w: WindowState): string {
 return (w.current_ciso_options?.[0] as any)?.risk_tier || '—';
}

(window as any).__wmToggleRisk = (tier: string, btn: HTMLElement) => {
 if (_riskFilter.has(tier)) {
  _riskFilter.delete(tier);
  btn.classList.remove('active');
 } else {
  _riskFilter.add(tier);
  btn.classList.add('active');
 }
 _saveRiskFilter();
 window.dispatchEvent(new CustomEvent('wm-filter-change'));
};

(window as any).__wmSetSort = (mode: SortMode) => {
 _setSortMode(mode);
 document.querySelectorAll('.wm-sort-btn').forEach(b => {
  b.classList.toggle('active', (b as HTMLElement).dataset.sort === mode);
 });
 window.dispatchEvent(new CustomEvent('wm-filter-change'));
};

function _sortActive(windows: WindowState[]): WindowState[] {
 if (_sortMode === 'time') {
  return [...windows].sort((a, b) => b.created_at_ms - a.created_at_ms);
 }
 return [...windows].sort((a, b) => {
  const tA = _TIER_ORDER[_windowTopTier(a)] ?? 6;
  const tB = _TIER_ORDER[_windowTopTier(b)] ?? 6;
  if (tA !== tB) return tA - tB;
  return (b.phase_score || 0) - (a.phase_score || 0);
 });
}

// ── Main render ───────────────────────────────────────────────────────────────
export function renderWindowsPanel(windows: WindowState[], nowMs: number = Date.now()): string {
 if (!windows || windows.length === 0) {
  return '<div class="empty-state">Nenhuma janela activa. Aguardando triggers...</div>';
 }

 const active  = windows.filter(w => {
  if (w.is_closed) return false;
  const cnt = w.alert_count || (w as any).alerts?.length || 0;
  return cnt > 0;
 });
 const closed  = windows.filter(w => w.is_closed);
 const scored  = active.filter(w => (w.phase_score || 0) >= _minScore);
 const byRisk  = _riskFilter.size === 0
  ? scored
  : scored.filter(w => _riskFilter.has(_windowTopTier(w)));
 const visible = _sortActive(byRisk);
 const hidden  = active.length - visible.length;

 const activeCards = visible.length > 0
  ? visible.map(w => renderCard(w, true, nowMs)).join('')
  : `<div class="empty-state" style="grid-column:1/-1;font-size:11px;padding:10px">
    ${active.length > 0
     ? `${hidden} janela${hidden!==1?'s':''} oculta${hidden!==1?'s':''} — score &lt; ${_minScore}`
     : 'Nenhuma janela activa.'}
   </div>`;

 const closedSection = closed.length > 0 ? `
  <div class="wm-section-label closed" style="grid-column:1/-1">📋 FECHADAS (${closed.length})</div>
  ${closed.slice(0, 15).map(w => renderCard(w, false, nowMs)).join('')}
 ` : '';

 return `${activeCards}${closedSection}`;
}

// ── Alert timeline ────────────────────────────────────────────────────────────
function getTs(a: AlertPayload): number {
 // a.ts is ISO string built by convertAlertToPayload
 if (a.ts) {
  const t = new Date(a.ts).getTime();
  if (t > 0) return t;
 }
 // fallback: raw timestamp_ms from SSE payload (may survive as any)
 const raw = (a as any).timestamp_ms;
 if (raw != null && raw > 0) return raw;
 return 0; // unknown — do not use Date.now() as it would show current time
}

function renderTimeline(alerts: AlertPayload[], createdMs: number, expiresMs: number, phases: string[]): string {
 if (!alerts.length)
  return '<div class="wm-no-alerts">⏳ Nenhum alerta nesta janela ainda</div>';

 const span   = expiresMs - createdMs || 1;
 const sorted = [...alerts].sort((a, b) => getTs(a) - getTs(b));
 const uid    = `tl${Math.random().toString(36).slice(2,8)}`;

 const pins = sorted.map((a, i) => {
  const ts        = getTs(a);
  const pct       = ts > 0
   ? Math.max(2, Math.min(97, ((ts - createdMs) / span) * 100))
   : Math.max(2, Math.min(97, (i / Math.max(1, sorted.length - 1)) * 97));
  const phase     = a.kill_chain || a.phases_detected?.[0] || phases[i] || '';
  const isNoise   = (a as any).is_noise || false;
  const isTrigger = i === 0;
  const color     = isNoise ? '#64748b' : (PHASE_COLORS[phase] || '#94a3b8');
  const abbr      = isNoise ? 'NS' : (PHASE_ABBRS[phase] || phase.slice(0,2) || 'AL');
  const timeStr   = ts > 0
   ? new Date(ts).toLocaleTimeString('pt-PT').slice(0,5)
   : '—';
  const sevColor  = a.severity === 'critical' ? '#dc2626'
          : a.severity === 'high'     ? '#ea580c'
          : a.severity === 'medium'   ? '#d97706' : '#22c55e';

  const size    = isTrigger ? '15px' : isNoise ? '8px' : '13px';
  const border  = isTrigger ? `3px solid ${sevColor}` : `1.5px solid ${sevColor}`;
  const glow    = isTrigger
   ? `box-shadow:0 0 0 3px rgba(34,211,238,.35),0 0 8px ${color};`
   : `box-shadow:0 0 4px ${color};`;
  
  return `
   <div class="wm-pin ${uid}"
    style="position:absolute;left:${pct}%;top:50%;transform:translate(-50%,-50%);
       width:${size};height:${size};border-radius:50%;background:${color};
       border:${border};cursor:pointer;z-index:${isTrigger?15:10};
       transition:transform .15s;${glow}${isNoise?'opacity:.6;':''}"
    title="${esc('#'+(a.number||'?')+' · '+(a.title||a.category||abbr)+' · '+timeStr)}"
    ${isTrigger
     ? `data-push-category="${esc(a.category||'')}"
      data-push-number="${esc(a.number||'')}"
      data-push-severity="${esc(a.severity||'')}"
      data-push-killchain="${esc(a.kill_chain||'')}"
      data-push-ts="${esc(a.ts||'')}"
      data-push-windowid="${esc(a.window_id||'')}"
      onclick="window.__wmPushAlertToExtension(this)"`
     : ''}>
    <div style="position:absolute;top:calc(100% + 4px);left:50%;transform:translateX(-50%);
      color:${color};font-size:8px;font-weight:700;
      white-space:nowrap;font-family:monospace;
      display:block;pointer-events:none;z-index:20;text-align:center;">
 ${isTrigger?'▶ ':''}${abbr}
</div>
   </div>`;
 }).join('');

 const t0 = new Date(getTs(sorted[0])).toLocaleTimeString('pt-PT').slice(0,5);
 const tN = sorted.length > 1
  ? new Date(getTs(sorted[sorted.length-1])).toLocaleTimeString('pt-PT').slice(0,5)
  : '';

 return `
  <style>
   .${uid}:hover{transform:translate(-50%,-50%) scale(1.35)!important;z-index:30;}
   .${uid}:hover>div{display:block!important;}
  </style>
  <div style="position:relative;height:32px;margin:4px 0 2px">
   <div style="position:absolute;top:50%;left:0;right:0;height:2px;
         background:linear-gradient(90deg,var(--cyan),#475569);
         transform:translateY(-50%);border-radius:2px"></div>
   ${pins}
   <div style="position:relative;height:14px">
    <div style="position:absolute;left:0;bottom:4px;font-size:8px;font-family:monospace;color:var(--text4)">${t0}</div>
    ${tN?`<div style="position:absolute;right:0;bottom:-2px;font-size:8px;font-family:monospace;color:var(--text4)">${tN}</div>`:''}
   </div>
  </div>`;
}

// ── Window card ───────────────────────────────────────────────────────────────
function _closedBadge(w: WindowState): string {
  const confirmed_by    = (w as any).confirmed_by    || '';
  const confirmed_label = (w as any).confirmed_label || '';
  const close_reason    = (w as any).close_reason    || '';
  const hasReport       = !!confirmed_label;

  if (confirmed_by === 'operator' || close_reason.startsWith('✋'))
    return `<div class="wm-closed operator">✋ Confirmado pelo analista</div>`;

  if (confirmed_by === 'finish' || close_reason.startsWith('⏹'))
    return `<div class="wm-closed" style="opacity:.6">⏹ Finalizado</div>`;

  if (hasReport)
    return `<div class="wm-closed auto">⚡ ${esc(confirmed_label)} — relatório gerado</div>`;

  if (confirmed_by === 'timeout' || close_reason === 'timeout')
    return `<div class="wm-closed timeout" style="opacity:.6">⏱ Timeout — sem relatório</div>`;

  // close_reason pode ser "convergence" ou vazio — se veio de SSE window_closed
  // sem hypothesis_confirmed associado, não temos confirmed_label
  if (confirmed_by === 'done')
    return `<div class="wm-closed" style="opacity:.6">⏹ Dataset concluído</div>`;

  return `<div class="wm-closed" style="opacity:.6">✓ Fechada</div>`;
}

function renderCard(w: WindowState, isActive: boolean, nowMs: number = Date.now()): string {
 const alerts  = ((w as any).alerts || []) as AlertPayload[];
 const phases  = w.phases || [];
 const options = w.current_ciso_options || [];
 const score   = w.phase_score || 0;
 const top     = options[0];
 const topPct  = top ? Math.round(top.probability * 100) : 0;
 const topCol  = topPct > 80 ? '#dc2626' : topPct > 60 ? '#ea580c' : '#d97706';
 const createdT = new Date(w.created_at_ms).toLocaleTimeString('pt-PT').slice(0,5);
 const expiresT = new Date(w.expires_at_ms).toLocaleTimeString('pt-PT').slice(0,5);

 // ── Closed card: minimal ──────────────────────────────────────────────────
 if (!isActive) {
  const closedLabel = (w as any).confirmed_label
    || (w.current_ciso_options?.[0] as any)?.category
    || '';
  const closedBadge = closedLabel ? getCategoryBadge(closedLabel) : esc(w.window_id.slice(0,8));
  const confirmedProb = (w as any).confirmed_probability;
  const closedPct = confirmedProb != null && confirmedProb > 0
    ? `${Math.round(confirmedProb * 100)}%`
    : topPct > 0 ? `${topPct}%` : '';
  
  const alertNumbers = ((w as any).alerts || [])
    .map((a: any) => a.number).filter((n: string) => n && n !== '—').join(', ');

  return `
  <div class="wm-card closed" data-window-id="${esc(w.window_id)}">
    <div class="wm-line1">
      <span class="wm-timerange">${createdT} → ${expiresT}</span>
      <span class="wm-pill wm-badge-impact" style="color:${topCol};border-color:${topCol}33">
        ${closedBadge} ${closedPct}
      </span>
      <span class="wm-pill" style="margin-left:auto">Score: ${score}</span>
    </div>
    ${alertNumbers ? `
    <div style="padding:2px 6px 4px;font-family:var(--mono);font-size:9px;color:var(--text4)">
      📋 ${esc(alertNumbers)}
    </div>` : ''}
    ${_closedBadge(w)}
  </div>`;
}

 const remaining = Math.max(0, w.expires_at_ms - nowMs);
 const minL      = Math.floor(remaining / 60000);
 const secL      = Math.floor((remaining % 60000) / 1000);
 const timerStr  = `${minL}:${secL.toString().padStart(2,'0')}`;
 const critical  = remaining < 60000;

 const CONFIRM_THRESHOLD_PCT = 85;
 const SHOW_CONFIRM_PCT      = 75;
 const showTimer   = isActive && topPct >= CONFIRM_THRESHOLD_PCT && remaining > 0;
 const showExpired = isActive && topPct >= CONFIRM_THRESHOLD_PCT && remaining === 0;
 const showConfirm = isActive && topPct >= SHOW_CONFIRM_PCT;

 const topTierCol = topPct >= 85 ? '#dc2626' : topPct >= 70 ? '#ea580c' : topPct >= 50 ? '#d97706' : '#64748b';
 const _hhmm      = (ms: number) => ms ? new Date(ms).toLocaleTimeString('pt-PT').slice(0,5) : '—';
 const tierShort  = (t: string)  => t.replace('MEDIUM-HIGH','MH').replace('MEDIUM','ME')
                   .replace('CRITICAL','CR').replace('HIGH','HI')
                   .replace('LOW-MED','LM').replace('LOW','LO');
 const tierCol    = (t: string)  => t === 'CRITICAL' ? '#dc2626' : t === 'HIGH' ? '#ea580c' :
                  t.includes('MEDIUM') ? '#d97706' : '#64748b';
 const modeBadge  = (w as any).window_mode === 'adaptive'
  ? '<span class="wm-mode adaptive">⚡</span>' : '';

 const timerInline = showTimer
  ? `<span class="wm-timer-inline${critical?' critical':''}" data-expires="${w.expires_at_ms}" data-confirm-pct="${topPct}">⏱ ${timerStr}</span>`
  : showExpired
   ? `<span class="wm-timer-inline expired" data-expires="${w.expires_at_ms}">⏳ A confirmar...</span>`
   : '';

 const phaseLine = phases.length > 0
  ? `<span style="font-size:10px">🎯 ${phases.length} Fase${phases.length!==1?'s':''}: ${
      phases.map((p,i) =>
        `<span style="color:${PHASE_COLORS[p]||'#64748b'}">${PHASE_ABBRS[p]||p.slice(0,2)}</span>${i<phases.length-1?'→':''}`
      ).join('')}</span>`
  : '';

 const phaseForHyp = (cat: string): { num: string; alert: AlertPayload | null } => {
  const kw = cat.toLowerCase().split(/\s+/).filter(x => x.length > 4);
  const match = [...alerts].reverse().find(a =>
   kw.some(k => (a.category||'').toLowerCase().includes(k) || (a.kill_chain||'').toLowerCase().includes(k))
  ) || alerts[0] || null;
  const num = match?.number || '';
  const isValidNum = num && !num.startsWith('W') && num.length < 20;
  return { num: isValidNum ? num : '', alert: match || null };
 };

 const hypothesesHtml = options.length > 0 ? `
  <div class="wm-hyps">
   ${options.slice(0,3).map((o,idx) => {
    const pct  = Math.round(o.probability*100);
    const tier = (o as any).risk_tier || '—';
    const tc   = tierCol(tier);
    const ts   = tierShort(tier);
    const { num, alert: evAlert } = phaseForHyp(o.category);
    const isTop = idx === 0;
    const evHtml = num && evAlert ? `
     <span class="wm-hyp-ev clickable"
      title="Carregar alerta #${esc(num)} na extensão para análise SIEM"
      data-push-category="${esc(evAlert.category||'')}"
      data-push-number="${esc(num)}"
      data-push-severity="${esc(evAlert.severity||'')}"
      data-push-killchain="${esc(evAlert.kill_chain||'')}"
      data-push-ts="${esc(evAlert.ts||'')}"
      data-push-windowid="${esc(evAlert.window_id||w.window_id)}"
      onclick="window.__wmPushAlertToExtension(this)">
      🔍 #${esc(num)}
     </span>` : '';
    return `<div class="wm-hyp-row${isTop?' top':''}">
     <div class="wm-hyp-info">
      <span class="wm-hyp-name${isTop?' top':''}" style="color:${isTop?tc:'var(--text4)'}">${esc(o.category)}</span>
      ${evHtml}
     </div>
     ${showConfirm
      ? `<button class="wm-hyp-btn${isTop?' top':''}"
            style="background:${tc}${isTop?'22':'11'};border-color:${tc}${isTop?'55':'28'};color:${tc}"
            data-confirm-btn="${esc(w.window_id)}"
            onclick="window.__wmConfirmHypothesis('${esc(w.window_id)}','${esc(o.category)}')"
            title="${esc(o.category)} — ${tier}">
            ${getCategoryBadge(o.category)} ${ts} ${pct}%
        </button>`
      : `<span class="wm-hyp-pct-badge" style="color:${tc}">${pct}%</span>`
  }
    </div>`;
   }).join('')}
  </div>`
  : '<div class="wm-analyzing">🔍 A analisar...</div>';
 
  // Extrair os números dos alertas (mesma lógica do agent2.ts)
  const alertNumbers = (() => {
      const alertIds = alerts.map(a => a.number).filter(n => n && n !== '—');
      if (alertIds.length > 0) {
          return alertIds.join(', ');
      }
      return '';
  })();

  const alertNumbersHtml = alertNumbers
  ? `<span style="font-family:var(--mono);font-size:9px;color:var(--cyan-hi)">📋 ${esc(alertNumbers)}</span>`
  : '';

 return `
  <div class="wm-card active" data-window-id="${esc(w.window_id)}">
   <div class="wm-line1">
    <span style="font-family:var(--mono);font-size:9px;color:var(--text4)">ID: ${esc(w.window_id)}</span>
    <span class="wm-timerange" style="color:${topTierCol}">🕐 ${_hhmm(w.created_at_ms)} → ${_hhmm(w.expires_at_ms)}</span>
    <span class="wm-pill">${alerts.length} alerta${alerts.length!==1?'s':''}</span>
    <span class="wm-pill">Score: ${score}</span>
   </div>
   <div class="wm-line1">
    ${alertNumbersHtml}
   </div>
   <div class="wm-line1">
    ${phaseLine}
   </div>
   ${renderTimeline(alerts, w.created_at_ms, w.expires_at_ms, phases)}
   <div class="wm-line1">
    <span style="margin-left:auto;display:flex;align-items:center;gap:4px">${timerInline}${modeBadge}</span>
   </div>
   ${hypothesesHtml}
  </div>`;
}