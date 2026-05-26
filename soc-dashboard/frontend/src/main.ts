import "./style.css";
import { APP_TEMPLATE } from "./boot/template";
import { STORAGE_KEYS } from "./core/constants";
import { addWindow, updateWindowAlert, closeWindow, addAlert, setAlerts } from "./core/store";
import { renderAgent2Panel, wireAgent2Events } from "./components/agent2";
import type { HypothesisGraphState, WindowState, AlertPayload } from "./core/types";
import {
getAlerts, getAgent2Reports, getConnection, getTotalReceived,
setConnection, setAgent2Reports, persistAgent2, setTotalReceived,
loadPersistedState, setRenderCallback,
} from "./core/store";
import { renderConnectionBadge } from "./components/footer";
import {
wireSliceControls,
startCountdown, stopCountdown,
updateCurrentAlertDisplay, updateNextAlertInfo,
updateNextAlertTimer, setSpeedFactor, calculateSimulatedSeconds,
setOnSeekCommit, setDatasetBounds,
} from "./components/slice";
import { renderHypothesisGraph } from "./components/graph_viz";
import { renderWindowsPanel } from "./components/windows_panel";
import { logger, logSSEEvent, logWindowOp, logHypothesisConfirmed, logError } from "./core/logger";
import { renderAlertTimelineSVG, setupTimelineClickHandler, setupTimelineScroll, scrollToEndInstant, type TimelineAlert } from "./components/alert_timeline";

const MODULE = "Dashboard";

let _es: EventSource | null = null;
let _windowTimeouts: Map<string, ReturnType<typeof setTimeout>> = new Map();
let _graphState: HypothesisGraphState | null = null;
let _activeWindows: WindowState[] = [];
let _pendingRequests: Set<number> = new Set();
let _sentAlerts: Set<number> = new Set();
// Stream clock — last alert timestamp from the dataset (for historical replays)
let _streamNowMs: number = 0;
// Stream advance rate — dataset ms per real second (interpolated between alerts)
let _streamRateMs: number = 0;
let _alertsByNumber: Map<string, any> = new Map();
let _rawAlertsByNumber: Map<string, any> = new Map();

setRenderCallback(() => renderFull());

function setText(id: string, html: string): void {
const el = document.getElementById(id);
if (el && el.innerHTML !== html) el.innerHTML = html;
}

// Pending confirmations waiting for report generation
let _pendingReports: Set<string> = new Set();

// Trigger alert per window — number of the alert that opened each window
const _windowTriggers: Map<string, string> = new Map();

function _updatePendingBadge(): void {
const badge  = document.getElementById('reports-pending-badge');
const count  = document.getElementById('reports-pending-count');
const n      = _pendingReports.size;
if (badge) {
 badge.style.display = n > 0 ? '' : 'none';
 badge.title = n > 0
 ? `Em geração:\n${[..._pendingReports].join('\n')}`
 : '';
}
if (count) count.textContent = String(n);
}

function updateTimelineDisplay(): void {
const alerts = getAlerts();
_alertsByNumber = new Map(alerts.map(a => [String(a.number), a]));
const content = document.getElementById("timeline-content");
const badge = document.getElementById("timeline-alert-count");
if (!content) return;

if (!alerts.length) {
 content.innerHTML = `<div class="timeline-strip-scroll" id="timeline-scroll-container" style="overflow-x: scroll !important;">
 <div class="timeline-empty-state">
  <div class="empty-icon">📡</div>
  <div>Aguardando alertas...</div>
 </div>
 </div>`;
 if (badge) badge.textContent = "0";
 return;
}

const ta: TimelineAlert[] = alerts.map(a => ({
 number: a.number, 
 timestamp_ms: new Date(a.ts).getTime(),
 category: a.category, 
 type: a.category || a.title || "",
 phase: a.kill_chain || a.phases_detected?.[0], 
 severity: a.severity, 
 window_id: a.window_id,
 is_noise:     a.is_noise === true, 
}));

const latestTrigger = _activeWindows.length > 0
 ? _windowTriggers.get(_activeWindows[0].window_id)
 : undefined;

// Renderiza com container de scroll forçado
content.innerHTML = `
 <div class="timeline-strip-scroll" id="timeline-scroll-container" style="overflow-x: scroll !important; width: 100%;">
  ${renderAlertTimelineSVG({
    alerts: ta,
    height: 72,
    selectedAlertNumber: latestTrigger,
    onAlertClick: (_alert: TimelineAlert) => {},
})}
 </div>
`;

if (badge) badge.textContent = `${alerts.length}`;

// Setup scroll com forçagem de barra visível
setupTimelineScroll('timeline-scroll-container');

// Scroll para o alerta mais recente com delay para garantir renderização
setTimeout(() => {
 scrollToEndInstant();
 // Força a barra de scroll a aparecer novamente
 const scrollDiv = document.getElementById('timeline-scroll-container');
 if (scrollDiv) {
 scrollDiv.style.overflowX = 'scroll';
 }
}, 50);
}

function renderFull(): void {
const agent2Reports = getAgent2Reports();
const totalReceived = getTotalReceived();

updateTimelineDisplay();
setText("hypothesis-graph", renderHypothesisGraph(_graphState));
setText("windows-panel", renderWindowsPanel(_activeWindows, _streamNowMs || Date.now()));
// Push confirmable window context to the extension proactively
_activeWindows.filter(w => !w.is_closed).forEach(_pushWindowContextToExtension);
setText("agent2-panel", renderAgent2Panel([], 0, agent2Reports, {}));

setText("footer-chips",
 `<span class="fchip">Alerts <span class="val">${totalReceived}</span></span>` +
 `<span class="fchip">Windows <span class="val">${_activeWindows.filter(w => !w.is_closed).length}</span></span>` +
 `<span class="fchip">Nodes <span class="val">${_graphState?.nodes?.length || 0}</span></span>` +
 `<span class="fchip">Confirmed <span class="val" style="color:#22c55e">${_graphState?.confirmed_hypotheses?.length || 0}</span></span>`
);

const awB = document.getElementById("active-windows-badge");
if (awB) awB.textContent = `${_activeWindows.filter(w => !w.is_closed).length} ativas`;
const rB = document.getElementById("reports-count-badge");
if (rB) rB.textContent = `${agent2Reports.length}`;

setText("footer-conn", renderConnectionBadge(getConnection()));
}

function startWindowTimeout(windowId: string, expiresAt: number): void {
  // Window lifecycle is managed server-side via SSE window_closed events.
  // Frontend timeout is only a safety fallback using real elapsed time.
  if (_windowTimeouts.has(windowId)) clearTimeout(_windowTimeouts.get(windowId));
  // Only set a fallback timeout if expiresAt is in the future relative to now
  const msFromNow = expiresAt - Date.now();
  if (msFromNow > 0 && msFromNow < 60 * 60 * 1000) {
    _windowTimeouts.set(windowId, setTimeout(() => {
      closeWindow(windowId, "timeout");
      renderFull();
    }, msFromNow));
  }
  // If expiresAt is in the past (historical dataset), do NOT close — wait for SSE
}

// Sync the window-mode button label with the actual server-side value
function _applyWindowModeBtn(mode: string): void {
const btn = document.getElementById('btn-window-mode') as HTMLButtonElement | null;
if (!btn) return;
const isAdaptive = mode === 'adaptive';
btn.textContent = isAdaptive ? '⚡ adaptive' : '📐 fixed';
btn.classList.toggle('wm-mode-adaptive', isAdaptive);
}

function _applyGridCols(cols: number): void {
const area = document.getElementById("windows-panel");
if (area) area.style.setProperty("--wm-cols", String(cols));
document.querySelectorAll(".grid-btn").forEach(b => {
 b.classList.toggle("active", parseInt((b as HTMLElement).dataset.cols || "0", 10) === cols);
});
}

function wireEvents(): void {
document.getElementById("btn-clear-session")?.addEventListener("click", () => {
 if (!confirm("Clear session data and reset?")) return;
 Object.values(STORAGE_KEYS).forEach(k => sessionStorage.removeItem(k));
 _sentAlerts.clear();
 _pendingRequests.clear();
 location.reload();
});

// Sync window mode button with server .env value on startup
fetch('/api/config')
 .then(r => r.ok ? r.json() : null)
 .then(cfg => { if (cfg?.window_mode) _applyWindowModeBtn(cfg.window_mode); })
 .catch(() => {});

// Hypothesis Graph overlay
const overlay  = document.getElementById("graph-overlay")!;
const backdrop = document.getElementById("graph-overlay-backdrop")!;
document.getElementById("btn-graph-toggle")?.addEventListener("click", () => {
 overlay.style.display = overlay.style.display === "none" ? "flex" : "none";
});
document.getElementById("btn-graph-close")?.addEventListener("click", () => {
 overlay.style.display = "none";
});
backdrop?.addEventListener("click", () => { overlay.style.display = "none"; });
document.addEventListener("keydown", (e: KeyboardEvent) => {
 if (e.key === "Escape") overlay.style.display = "none";
});

// ── Finish button — force-close all active windows and produce classification log ──
document.getElementById("btn-finish")?.addEventListener("click", async () => {
 const btn    = document.getElementById("btn-finish") as HTMLButtonElement;
 const active = _activeWindows.filter(w => !w.is_closed);
 if (active.length === 0) { alert("Não há janelas activas para finalizar."); return; }
 if (!confirm(
 `Forçar conclusão de ${active.length} janela${active.length !== 1 ? 's' : ''} activa${active.length !== 1 ? 's' : ''}?\n\n` +
 `Todas as janelas serão fechadas e um log de classificações CISO gerado para comparação académica com o dataset.`
 )) return;

 btn.disabled = true;
 btn.textContent = "⏳ A processar...";
 try {
 const res = await fetch("/api/agent1/finish", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
  windows: active.map(w => ({
   window_id:      w.window_id,
   top_hypothesis: (w.current_ciso_options?.[0] as any)?.category || "",
   probability:    (w.current_ciso_options?.[0] as any)?.probability || 0,
   risk_tier:      (w.current_ciso_options?.[0] as any)?.risk_tier || "—",
   all_hypotheses: (w.current_ciso_options || []).map((o: any) => ({
   category: o.category, probability: o.probability, risk_tier: o.risk_tier,
   })),
   phases:        w.phases || [],
   phase_score:   w.phase_score || 0,
   alert_count:   w.alert_count || 0,
   created_at_ms: w.created_at_ms,
   expires_at_ms: w.expires_at_ms,
   alerts: ((w as any).alerts || []).map((a: any) => ({
   number:   a.number || a.Number || "",
   category: a.category || a.Category || "",
   phase:    a.kill_chain || a.phase || a.Phase || "",
   severity: a.severity || a.Severity || "",
   ts:       a.ts || "",
   })),
  })),
  }),
 });
 if (!res.ok) throw new Error(`HTTP ${res.status}`);
 const data = await res.json();
 // Close all in frontend
 active.forEach(w => {
  const ci = _activeWindows.findIndex(x => x.window_id === w.window_id);
  if (ci >= 0) _activeWindows[ci] = {
  ..._activeWindows[ci], 
  is_closed: true,
  close_reason: "⏹ Finalizado", 
  confirmed_by: "finish",
  } as any;
 });
 renderFull();
 btn.textContent = "✓ Concluído";
 (btn as HTMLButtonElement).style.color = "#22c55e";
 if (data.log_file) setTimeout(() =>
  alert(`✓ Log gerado: ${data.log_file}\n\n${data.summary || ""}\n\nVerifica a pasta reports/ do projecto.`), 300);
 } catch (e) {
 btn.textContent = "⏹ Finish";
 btn.disabled = false;
 alert(`Erro: ${e}`);
 }
});

// Windows grid column picker
const savedCols = parseInt(sessionStorage.getItem("wm_cols") || "4", 10);
_applyGridCols(savedCols);
document.querySelectorAll(".grid-btn").forEach(btn => {
 btn.addEventListener("click", () => {
 const cols = parseInt((btn as HTMLElement).dataset.cols || "2", 10);
 _applyGridCols(cols);
 sessionStorage.setItem("wm_cols", String(cols));
 });
});
}

function convertAlertToPayload(alert: any, windowId?: string): AlertPayload {
return {
 number: alert.number || alert.Number || alert.alert_id || String(alert.index || ""),
 title: alert.title || `${alert.category || alert.Category || ""} / ${alert.type || alert.Type || ""}`,
 severity: alert.severity || alert.Severity || "medium",
 category: alert.category || alert.Category || "",
 ts: alert.ts
 || (alert.timestamp_iso && alert.timestamp_iso !== '' ? alert.timestamp_iso : null)
 || (alert.timestamp_ms != null && alert.timestamp_ms > 0
   ? new Date(alert.timestamp_ms).toISOString()
   : (alert._timestamp_ms != null && alert._timestamp_ms > 0
     ? new Date(alert._timestamp_ms).toISOString()
     : new Date(alert.TimestampMs || 0).toISOString() || new Date().toISOString())),
 source: alert.source || alert.Source || "Agent1",
 affected_asset: alert.affected_asset || alert.AffectedAsset || "",
 mitre: alert.mitre || alert.Mitre || "",
 kill_chain: alert.phase || alert.Phase || "",
 phases_detected: alert.phases_detected || (alert.phase || alert.Phase ? [alert.phase || alert.Phase] : []),
 classifications: [], primary_ciso: { ciso_category_id: 0, ciso_category_name: "", risk_tier: "—", plausibility: 0 },
 soc_routing: "", tlp: "green", tags: "", emitted_at: new Date().toISOString(),
 detected_threat_type: "", ciso_state: "", phase_score: 0,
 trigger_type: "alert", discard_reason: "", is_discarded: false, 
 window_id: windowId,
 timestamp_ms: alert.timestamp_ms || alert._timestamp_ms || 0,  
 is_noise:     alert.is_noise === true,
};
}

// ── Extension integration ─────────────────────────────────────────────────────
// Tracks which windows have already pushed context to the extension
const _pushedToExtension: Set<string> = new Set();
const EXT_PUSH_THRESHOLD = 75; // push context when hypothesis reaches 75%

function _pushWindowContextToExtension(w: any): void {
  if (_pushedToExtension.has(w.window_id)) return;
  const options = w.current_ciso_options || [];
  const topPct  = options[0] ? Math.round(options[0].probability * 100) : 0;
  if (topPct < EXT_PUSH_THRESHOLD) return;

  const alerts = (w.alerts || []) as any[];
  const cveRe  = /CVE-\d{4}-\d{4,}/gi;
  const cves: string[] = [];
  const seen = new Set<string>();
  alerts.forEach((a: any) => {
    const text = JSON.stringify(a);
    let m: RegExpExecArray | null;
    cveRe.lastIndex = 0;
    while ((m = cveRe.exec(text)) !== null) {
      const c = m[0].toUpperCase();
      if (!seen.has(c)) { seen.add(c); cves.push(c); }
    }
  });

  _pushedToExtension.add(w.window_id);
  window.postMessage({
    type:        'REDSHIFT_WINDOW_CONTEXT',
    windowId:    w.window_id,
    label:       options[0]?.category || '',
    probability: options[0]?.probability || 0,
    tier:        options[0]?.risk_tier || '',
    cves,
    iocs:        [],
    phases:      w.phases || [],
    assets:      [],
    ...((): { siemAlert: any } => {
      const triggerNum = _windowTriggers.get(w.window_id);
      const rawTrigger = triggerNum ? _rawAlertsByNumber.get(triggerNum) : null;
      console.log('[EXT] window_id:', w.window_id, 
            'triggerNum:', triggerNum, 
            'rawTrigger:', rawTrigger,
            'rawKeys:', [..._rawAlertsByNumber.keys()].slice(0,5));
      const _INT = new Set(['AGENT1_', 'AGENT1', 'AGENT2']);
      const clean = (o: Record<string, any>) =>
        Object.fromEntries(Object.entries(o).filter(([, v]) => v !== '' && v != null));
      return {
        siemAlert: clean(rawTrigger ? {
          'alert_number':   rawTrigger.Number        || '',
          'title':          rawTrigger.Title         || '',
          'description':    rawTrigger.Description   || '',
          'mitre_attack':   rawTrigger.MitreAttack   || '',
          'affected_asset': rawTrigger.AffectedAsset || '',
          'tags':           rawTrigger.Tags          || '',
          'tlp':            rawTrigger.TLP           || '',
          'priority':       rawTrigger.Priority      || '',
          'severity':       rawTrigger.Severity      || '',
          'source':         _INT.has(rawTrigger.Source || '') ? '' : (rawTrigger.Source || ''),
          'kill_chain':     (w.phases || []).join(' → '),
          'alert_count':    alerts.length,
          'cves_detected':  cves,
          'window_id':      w.window_id,
          'phase_score':    w.phase_score || 0,
          'hypothesis':     options[0]?.category || '',
          'risk_tier':      options[0]?.risk_tier || '',
        } : {
          'hypothesis':    options[0]?.category || '',
          'risk_tier':     options[0]?.risk_tier || '',
          'kill_chain':    (w.phases || []).join(' → '),
          'alert_count':   alerts.length,
          'cves_detected': cves,
          'window_id':     w.window_id,
          'phase_score':   w.phase_score || 0,
        }),
      };
    })(),
  }, '*');
}

async function requestProcessAlert(alertIndex: number, retryCount = 0): Promise<void> {
if (_sentAlerts.has(alertIndex) || _pendingRequests.has(alertIndex)) return;
_sentAlerts.add(alertIndex);
_pendingRequests.add(alertIndex);
try {
 const res = await fetch("/api/agent1/process-next", {
 method: "POST", headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ alert_index: alertIndex }),
 });
 _pendingRequests.delete(alertIndex);
 if ((res.status === 400 || res.status === 503) && retryCount < 10) {
 setTimeout(() => { _sentAlerts.delete(alertIndex); requestProcessAlert(alertIndex, retryCount + 1); }, 1000);
 }
} catch {
 _pendingRequests.delete(alertIndex);
 if (retryCount < 5) setTimeout(() => requestProcessAlert(alertIndex, retryCount + 1), 1000);
}
}

function connectSSE(): void {
_es = new EventSource("/events");

_es.onopen = () => { setConnection("connected"); renderFull(); };

_es.onmessage = (ev: MessageEvent<string>) => {
 try {
 const { type, payload } = JSON.parse(ev.data);
 logSSEEvent(MODULE, type, payload);

 switch (type) {
  case "alert": {
  const rawNum = String(payload.number || payload.Number || '');
  // Guarda o raw PRIMEIRO
  if (rawNum) _rawAlertsByNumber.set(rawNum, payload);

  // Depois re-tenta push para janelas que ficaram sem rawTrigger
  _activeWindows
    .filter(w => !w.is_closed && _pushedToExtension.has(w.window_id))
    .forEach(w => {
      const triggerNum = _windowTriggers.get(w.window_id);
      if (triggerNum === rawNum) {
        _pushedToExtension.delete(w.window_id);
        _pushWindowContextToExtension(w);
      }
    });

  const ap = convertAlertToPayload(payload, payload.window_id);
  (ap as any).is_noise = payload.is_noise === true;
  // Update stream clock for historical dataset replay
  const alertTs = payload.timestamp_ms || new Date(payload.ts || '').getTime();
  if (alertTs && alertTs > _streamNowMs) _streamNowMs = alertTs;
  if (!getAlerts().some(a => a.number === ap.number)) {
   addAlert(ap);
   setTotalReceived(getTotalReceived() + 1);
  }
  const i = _activeWindows.findIndex(w => w.window_id === payload.window_id);
  if (i >= 0) {
   const ea: AlertPayload[] = (_activeWindows[i] as any).alerts || [];
   if (!ea.some(a => a.number === ap.number)) ea.push(ap);
   _activeWindows[i] = { ..._activeWindows[i], alert_count: ea.length, alerts: ea } as any;
  }
  renderFull();
  break;
  }
  case "window_created": {
  logWindowOp(MODULE, "created", payload.window_id, {});
  // Record trigger alert number for timeline pin
  const triggerNum = String(
   payload.trigger_alert_number || payload.trigger_alert?.number ||
   payload.trigger_alert?.Number || ''
  );
  if (triggerNum) _windowTriggers.set(payload.window_id, triggerNum);

  // Convert trigger alert so the card shows ≥ 1 alert immediately
  const triggerAlertPayload = payload.trigger_alert
   ? convertAlertToPayload(payload.trigger_alert, payload.window_id)
   : null;
  const initialAlerts = triggerAlertPayload ? [triggerAlertPayload] : [];

  addWindow({
   windowId: payload.window_id, hypothesisLabel: payload.hypothesis_label || "Analyzing...",
   probability: payload.probability || 0, phaseScore: payload.phase_score || 0,
   phases: payload.phases || [], createdAt: payload.created_at_ms, expiresAt: payload.expires_at_ms,
   alerts: initialAlerts, isClosed: false, isConfirmed: false,
  });
  startWindowTimeout(payload.window_id, payload.expires_at_ms);
  _activeWindows = [{
   window_id:   payload.window_id,
   created_at_ms: payload.created_at_ms,
   expires_at_ms: payload.expires_at_ms,
   alert_count:   initialAlerts.length,
   phases:        payload.phases || [],
   phase_score:   payload.phase_score || 0,
   is_closed:     false,
   current_ciso_options: payload.ciso_options || [],
   alerts:        initialAlerts,
   window_mode:   payload.window_mode || 'fixed',
  } as any, ..._activeWindows].slice(0, 50);
  renderFull();
  break;
  }
  case "window_updated": {
  const i = _activeWindows.findIndex(w => w.window_id === payload.window_id);
  if (i >= 0) {
   const ea: any[] = (_activeWindows[i] as any).alerts || [];
   if (payload.alert && !ea.some((a: any) => a.number === payload.alert.number))
   ea.push(convertAlertToPayload(payload.alert, payload.window_id));
   _activeWindows[i] = {
   ..._activeWindows[i],
   alert_count: payload.alert_count || ea.length,
   phases: payload.phases || _activeWindows[i].phases,
   phase_score: payload.phase_score || _activeWindows[i].phase_score,
   current_ciso_options: payload.ciso_options || _activeWindows[i].current_ciso_options,
   // Update expires_at_ms — may change in adaptive mode when window is extended
   ...(payload.expires_at_ms ? { expires_at_ms: payload.expires_at_ms } : {}),
   // Preserve window_mode — set on window_created, carried through updates
   ...(payload.window_mode ? { window_mode: payload.window_mode } : {}),
   alerts: ea,
   } as any;
  }
  if (payload.alert) updateWindowAlert(payload.window_id, payload.alert);
  renderFull();
  break;
  }
  case "window_closed": {
  logWindowOp(MODULE, "closed", payload.window_id, { reason: payload.reason });
  closeWindow(payload.window_id, payload.reason);
  if (_windowTimeouts.has(payload.window_id)) {
   clearTimeout(_windowTimeouts.get(payload.window_id));
   _windowTimeouts.delete(payload.window_id);
  }
  const ci = _activeWindows.findIndex(w => w.window_id === payload.window_id);
  if (ci >= 0) {
   const existing = _activeWindows[ci] as any;
   // Don't overwrite if already operator-confirmed — preserve ✋ icon and label
   if (existing.confirmed_by !== 'operator') {
   _activeWindows[ci] = { ..._activeWindows[ci], is_closed: true, close_reason: payload.reason };
   } else {
   _activeWindows[ci] = { ..._activeWindows[ci], is_closed: true };
   }
  }
  renderFull();
  break;
  }
  case "graph_state_update": {
  _graphState = {
   nodes: payload.nodes || [], edges: payload.edges || [],
   confirmed_hypotheses: payload.confirmed_hypotheses || [],
   kill_chain_progress: payload.kill_chain_progress || {},
   total_evidence_windows: payload.total_evidence_windows || 0,
  };
  renderFull();
  break;
  }
  case "hypothesis_confirmed": {
  console.log('[CONFIRM]', payload);  
  const wid   = payload.window_id;
  const lbl   = payload.label || '';
  const meth  = payload.method || 'auto';
  logHypothesisConfirmed(MODULE, lbl, payload.score);
  // For non-operator confirms (timeout/auto), add to pending queue
  if (lbl && meth !== 'operator') {
   _pendingReports.add(lbl);
   _updatePendingBadge();
  }
  // Close the window card if not already closed by wm-operator-confirmed
  if (wid) {
   const ci = _activeWindows.findIndex(w => w.window_id === wid);
   if (ci >= 0 && ((_activeWindows[ci] as any).confirmed_by !== 'operator')) {
   const icon = meth === 'timeout' ? '⏱' : '⚡';
   _activeWindows[ci] = {
    ..._activeWindows[ci],
    is_closed: true,
    close_reason: `${icon} ${lbl}`,
    confirmed_by: meth,
    confirmed_label: lbl,
    confirmed_probability: payload.score || payload.probability || 0,
   } as any;
   }
  }
  renderFull();
  break;
  }
  case "dataset_bounds": {
  if (payload.speed_factor != null) setSpeedFactor(payload.speed_factor);
  setDatasetBounds(payload.dataMinMs, payload.dataMaxMs);
  if (payload.first_alert)
   updateCurrentAlertDisplay(payload.first_alert.number, payload.first_alert.category,
   payload.first_alert.type, payload.first_alert.timestamp_ms, 0, payload.total_alerts);
  if (payload.second_alert?.timestamp_ms) {
   const gapMs = payload.second_alert.timestamp_ms - payload.first_alert.timestamp_ms;
   const secs = calculateSimulatedSeconds(gapMs);
   updateNextAlertInfo(payload.second_alert.number || "?", payload.second_alert.category || "",
   payload.second_alert.type || "", payload.second_alert.timestamp_ms, Math.round(gapMs / 1000), secs);
   updateNextAlertTimer(secs);
  }
  // Sync window mode button with server-side value from .env
  if (payload.window_mode) _applyWindowModeBtn(payload.window_mode);
  requestProcessAlert(0);
  renderFull();
  break;
  }
  case "window_mode_changed": {
  if (payload.mode) _applyWindowModeBtn(payload.mode);
  break;
  }
  case "next_alert_info": {
  if (payload.is_last) { updateNextAlertTimer(0); stopCountdown(); }
  else {
   updateCurrentAlertDisplay(payload.current_alert_number || "?", payload.current_alert_category || "",
   payload.current_alert_type || "", payload.current_alert_timestamp_ms,
   payload.current_alert_index, payload.total_alerts || payload.current_alert_index + 1);
   const secs = calculateSimulatedSeconds(payload.gap_ms);
   // Stream advances gap_ms of dataset time in secs real seconds
   if (secs > 0 && payload.gap_ms > 0) {
   _streamRateMs = payload.gap_ms / secs;  // dataset ms per real second
   }
   updateNextAlertInfo(payload.next_alert_number || "?", payload.next_alert_category || "",
   payload.next_alert_type || "", payload.next_alert_timestamp_ms,
   Math.round(payload.gap_ms / 1000), secs);
   updateNextAlertTimer(secs);
   stopCountdown();
   startCountdown(secs, payload, () => requestProcessAlert(payload.next_alert_index));
  }
  renderFull();
  break;
  }
  case "ciso_report": {
  setAgent2Reports([payload, ...getAgent2Reports()].slice(0, 20));
  persistAgent2();
  // Extract confirmed labels — payload may have flat string[] or object[]
  const rawHyps = payload.confirmed_hypothesis_labels   // flat string[] (new)
   || payload.confirmed_hypotheses;                       // may be object[] (legacy)
  const confirmedLabels: string[] = Array.isArray(rawHyps)
   ? rawHyps.map((h: string | {label?: string}) =>
     typeof h === 'string' ? h : (h?.label ?? '')
    ).filter(Boolean)
   : (payload.metadata?.selected_hypothesis ? [payload.metadata.selected_hypothesis] : []);
  
  const reportProb = payload.decision?.selected_hypothesis?.probability;
  if (reportProb != null && reportProb > 0) {
    const reportAlertIds = new Set<string>([
      ...(payload.soc_report?.trigger_events || []).map((t: any) => String(t.id || '')),
      ...(payload.soc_report?.raw_alerts || []).map((a: any) => String(a.Number || a.number || '')),
    ].filter(Boolean));

    // Encontra a janela com MAIOR interseção — match exclusivo
    let bestIdx = -1;
    let bestScore = 0;

    _activeWindows.forEach((w, ci) => {
      const cl = (w as any).confirmed_label || '';
      const labelMatch = confirmedLabels.some(lbl =>
        cl && (cl === lbl || cl.includes(lbl) || lbl.includes(cl))
      );
      if (labelMatch) { bestIdx = ci; bestScore = 999; return; }

      if (reportAlertIds.size > 0) {
        const windowAlertIds = ((w as any).alerts || [])
          .map((a: any) => String(a.number || '')).filter(Boolean);
        const intersection = windowAlertIds.filter((id: string) => reportAlertIds.has(id)).length;
        if (intersection > bestScore) { bestScore = intersection; bestIdx = ci; }
      }
    });

    if (bestIdx >= 0 && bestScore > 0) {
      (_activeWindows[bestIdx] as any).confirmed_probability = reportProb;
      if (!(_activeWindows[bestIdx] as any).confirmed_label && confirmedLabels[0]) {
        (_activeWindows[bestIdx] as any).confirmed_label = confirmedLabels[0];
      }
    }
  }
   const payloadStr = JSON.stringify(payload);
  _pendingReports.forEach(lbl => {
   if (confirmedLabels.includes(lbl) || payloadStr.includes(lbl)) {
   _pendingReports.delete(lbl);
   }
  });
  _updatePendingBadge();
  renderFull();
  break;
  }
  case "done": {
  updateNextAlertTimer(0);
  stopCountdown();
  _activeWindows = _activeWindows.map(w =>
    w.is_closed ? w : {
      ...w,
      is_closed:    true,
      close_reason: '⏹ Dataset concluído',
      confirmed_by: 'done',
    } as any
  );
  renderFull();
  break;
}
default: logger.trace(MODULE, `Unhandled: ${type}`);
 }
 } catch (err) { logError(MODULE, "SSE parse error", err); }
};

_es.onerror = () => {
 _es?.close(); _es = null;
 setConnection("reconnecting");
 renderFull();
 setTimeout(connectSSE, 5000);
};
}

async function bootstrap(): Promise<void> {
loadPersistedState();
wireEvents();
wireSliceControls();
wireAgent2Events();

setupTimelineClickHandler((number: string) => {
  const a   = _alertsByNumber.get(number);
  const raw = _rawAlertsByNumber.get(number);
  if (!a) return;

  // Remove campos vazios — não enviar ruído ao LLM
  const clean = (obj: Record<string, any>) =>
    Object.fromEntries(
      Object.entries(obj).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
    );

  window.postMessage({
    type:        'REDSHIFT_WINDOW_CONTEXT',
    windowId:    a.window_id || '',
    label:       a.category  || '',
    probability: 0,
    tier:        a.severity  || '',
    cves:        [],
    iocs:        raw?.AffectedAsset ? [raw.AffectedAsset] : [],
    phases:      a.kill_chain ? [a.kill_chain] : (a.phases_detected || []),
    assets:      raw?.AffectedAsset ? [raw.AffectedAsset] : [],
    siemAlert: clean(raw ? {
      'alert_number':   String(raw.Number   || raw.number   || number),
      'external_id':    raw.ExternalId      || '',
      'tlp':            raw.TLP             || '',
      'priority':       raw.Priority        || '',
      'severity':       raw.Severity        || raw.severity  || '',
      'category':       raw.Category        || raw.category  || '',
      'type':           raw.Type            || raw.type      || '',
      'title':          raw.Title           || raw.title     || '',
      'source':         raw.Source          || raw.source    || '',
      'tags':           raw.Tags            || '',
      'mitre_attack':   raw.MitreAttack     || '',
      'affected_asset': raw.AffectedAsset   || '',
      'description':    raw.Description     || '',
      'use_case_tag':   raw.UseCaseTag      || '',
      'kill_chain':     a.kill_chain        || '',
      'timestamp':      raw.SiemDetectionTime || a.ts || '',
      'window_id':      a.window_id         || '',
      'assignee':       raw.Assignee        || '',
      'source_system':  'SOC Dashboard Timeline',
    } : {
      'alert_number':  number,
      'category':      a.category   || '',
      'kill_chain':    a.kill_chain  || '',
      'severity':      a.severity   || '',
      'timestamp':     a.ts         || '',
      'source_system': 'SOC Dashboard Timeline',
    }),
  }, '*');
});

// Seek commit — analyst moved a handle → reset current data and restart streaming
setOnSeekCommit(async (startMs: number, endMs: number) => {
 logger.info(MODULE, `Seek: ${new Date(startMs).toISOString()} → ${new Date(endMs).toISOString()}`);
 stopCountdown();

 // Clear all in-memory state
 _sentAlerts.clear();
 _pendingRequests.clear();
 _activeWindows = [];
 _graphState = null;
 _streamNowMs = 0;
 _streamRateMs = 0;
 _windowTriggers.clear();
 _pushedToExtension.clear();
 _pendingReports.clear();
 _updatePendingBadge();
 _windowTimeouts.forEach(t => clearTimeout(t));
 _windowTimeouts.clear();

 // Clear the alert store so the timeline SVG resets immediately
 setAlerts([]);

 // Reset timeline DOM instantly — don't wait for next renderFull
 const tlContent = document.getElementById('timeline-content');
 const tlBadge   = document.getElementById('timeline-alert-count');
 if (tlContent) tlContent.innerHTML = `<div class="timeline-empty-state"><div class="empty-icon">📡</div><div>A reiniciar...</div></div>`;
 if (tlBadge)   tlBadge.textContent = '0';

 // Reset windows panel instantly
 setText('windows-panel', '');

 try {
 await fetch("/api/agent1/seek", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ start_ms: startMs, end_ms: endMs }),
 });
 } catch (e) { logger.warn(MODULE, `Seek request failed: ${e}`); }
 renderFull();
});

// Windows panel score filter
window.addEventListener('wm-filter-change', () => renderFull());

// Operator confirmation — close card immediately, don't wait for SSE
window.addEventListener('wm-operator-confirmed', (e: Event) => {
 const { windowId, label } = (e as CustomEvent).detail;
 const ci = _activeWindows.findIndex(w => w.window_id === windowId);
 if (ci >= 0) {
 _activeWindows[ci] = {
  ..._activeWindows[ci],
  is_closed:       true,
  close_reason:    `✋ ${label}`,
  confirmed_by:    'operator',
  confirmed_label: label,
 } as any;
 }
 if (label) { _pendingReports.add(label); _updatePendingBadge(); }
 renderFull();
});
renderFull();
connectSSE();

const t0 = Date.now();
setInterval(() => {
 const s = Math.floor((Date.now() - t0) / 1000);
 const el = document.getElementById("footer-uptime");
 if (el) el.textContent = s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}, 1000);

// ── Window card timers — tick every second, smooth interpolation ──────────
setInterval(() => {
 if (_streamNowMs && _streamRateMs) _streamNowMs += _streamRateMs;
 const ref = _streamNowMs || Date.now();

 document.querySelectorAll<HTMLElement>('.wm-timer[data-expires]').forEach(el => {
 const expires = Number(el.dataset.expires);
 if (!expires || isNaN(expires)) return;
 const remaining = Math.max(0, expires - ref);

 if (remaining === 0) {
  // Timer expired — switch to "auto-confirming" state immediately
  // The server will emit window_closed/hypothesis_confirmed shortly after
  el.className = 'wm-timer-expired';
  el.textContent = '⏳ A confirmar automaticamente...';
  el.removeAttribute('data-expires'); // prevent further ticks on this element
  return;
 }

 const m = Math.floor(remaining / 60000);
 const s = Math.floor((remaining % 60000) / 1000);
 const txt = `⏱ ${m}:${s.toString().padStart(2, '0')}`;
 if (el.textContent !== txt) el.textContent = txt;
 el.classList.toggle('critical', remaining < 60000);
 });
}, 1000);

document.getElementById("debug-logs-btn")?.addEventListener("click", () => logger.downloadLogs());

setInterval(() => {
 fetch("/api/stream/status").then(r => r.json()).then(d => {
 const el = document.getElementById("stream-status");
 if (el) el.textContent = `📡 ${d.connected_clients} clientes · ${d.total_received} alertas`;
 }).catch(() => {});
}, 5000);

setInterval(async () => {
 try {
 const res = await fetch("/agent2-reports");
 if (!res.ok) return;
 const reps = await res.json();
 if (reps.length !== getAgent2Reports().length) { setAgent2Reports(reps); persistAgent2(); renderFull(); }
 } catch { /* no-op */ }
}, 5000);
}

document.getElementById("app")!.innerHTML = APP_TEMPLATE;
bootstrap();
