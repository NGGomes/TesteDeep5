import type { AlertPayload, IncidentHypothesis, SliceState, TriggerMeta, Agent2Report, WindowHypothesis} from './types';
import { DEFAULT_ACTIVE_WINDOW_MINUTES, STORAGE_KEYS } from './constants';

let _allAlerts: AlertPayload[] = [];
let _hypotheses: IncidentHypothesis[] = [];
let _windows: WindowHypothesis[] = [];
let _selectedHyp: number = 0;
let _connection: string = 'connecting';
let _totalReceived: number = 0;
let _agent2Reports: Agent2Report[] = [];
let _slice: SliceState = {
 dataMinMs: Date.now() - 7 * 24 * 60 * 60 * 1000,
 dataMaxMs: Date.now(),
 windowStartMs: Date.now() - DEFAULT_ACTIVE_WINDOW_MINUTES * 60 * 1000,
 windowEndMs: Date.now() };
let _triggerMeta: Map<string, TriggerMeta> = new Map();
let _renderScheduled = false;
let _renderCallback: (() => void) | null = null;

export function getAlerts(): AlertPayload[] { return _allAlerts; }
export function getWindows(): WindowHypothesis[] { return _windows; }
export function getSelectedHyp(): number { return _selectedHyp; }
export function getConnection(): string { return _connection; }
export function getTotalReceived(): number { return _totalReceived; }
export function getAgent2Reports(): Agent2Report[] { return _agent2Reports; }
export function getSlice(): SliceState { return { ..._slice }; }

export function setAlerts(alerts: AlertPayload[]): void { _allAlerts = alerts; }
export function setWindows(windows: WindowHypothesis[]): void { _windows = windows; }
export function setSelectedHyp(idx: number): void { _selectedHyp = idx; }
export function setConnection(conn: string): void { _connection = conn; }
export function setTotalReceived(total: number): void { _totalReceived = total; }
export function setAgent2Reports(reports: Agent2Report[]): void { _agent2Reports = reports; }
export function setSlice(slice: SliceState): void { _slice = { ...slice }; }
export function setTriggerMeta(meta: Map<string, TriggerMeta>): void { _triggerMeta = meta; }

export function addAlert(alert: AlertPayload): void {
 const meta = _triggerMeta.get(String(alert.number));
 if (meta) alert = { ...alert, ...meta };
 _allAlerts.push(alert);
 if (_allAlerts.length > 5000) _allAlerts.shift();
}

export function addWindow(window: WindowHypothesis): void {
 const existing = _windows.findIndex(w => w.windowId === window.windowId);
 if (existing >= 0) {
  _windows[existing] = window;
 } else {
  _windows.push(window);
 }
 _windows.sort((a, b) => b.createdAt - a.createdAt);
 if (_windows.length > 50) _windows = _windows.slice(0, 50);
 persistWindows();
 rebuildHypothesesFromWindows();
}

export function updateWindowAlert(windowId: string, alert: AlertPayload): void {
 const idx = _windows.findIndex(w => w.windowId === windowId);
 if (idx >= 0) {
  const existingAlert = _windows[idx].alerts.find(a => a.number === alert.number);
  if (!existingAlert) {
   _windows[idx].alerts.push(alert);
   persistWindows();
   rebuildHypothesesFromWindows();
   scheduleRender();
  }
 }
}

export function closeWindow(windowId: string, reason: 'timeout' | 'validation' | 'convergence'): void {
 const idx = _windows.findIndex(w => w.windowId === windowId);
 if (idx >= 0 && !_windows[idx].isClosed) {
  _windows[idx].isClosed = true;
  _windows[idx].closeReason = reason;
  if (reason === 'validation') {
   _windows[idx].isConfirmed = true;
   _windows[idx].confirmedAt = Date.now();
  }
  persistWindows();
  rebuildHypothesesFromWindows();
  scheduleRender();
 }
}

function rebuildHypothesesFromWindows(): void {
 const newHypotheses = _windows.filter(w => !w.isClosed).map((w) => ({
  id: w.windowId,
  windowStart: w.createdAt,
  windowEnd: w.expiresAt,
  tier: getTierFromProbability(w.probability),
  category: w.hypothesisLabel,
  mitreTechs: [],
  evidenceCount: w.alerts.length,
  evidenceGap: 0,
  isSevere: w.probability > 0.7,
  enisaDecision: w.probability > 0.7 ? 'Severe Incident' : 'Operational Noise',
  sources: ['SIEM', 'EDR'],
  killChains: w.phases.length,
  execAction: 'Under investigation',
  nis2: 'Monitor',
  gdpr: 'Monitor',
  alerts: w.alerts,
  anomalyScore: w.probability,
  reportText: '',
  detectedThreatType: w.hypothesisLabel,
  cisoState: w.probability > 0.85 ? 'CRITICAL_COMBINED_ATTACK' : w.probability > 0.7 ? 'INCIDENTE_GRAVE' : 'ATIVIDADE_SUSPEITA',
  phaseScore: w.phaseScore,
  phasesDetected: w.phases,
  triggerTypes: ['alert'],
  discardedCount: 0,
  discardReasons: [],
  windowId: w.windowId,
  expiresAt: w.expiresAt,
  isClosed: w.isClosed }));

 _hypotheses = newHypotheses as IncidentHypothesis[];
 if (_selectedHyp >= _hypotheses.length && _hypotheses.length > 0) _selectedHyp = 0;
 persistHypotheses();
}

function getTierFromProbability(prob: number): 'CRITICAL' | 'HIGH' | 'MEDIUM-HIGH' | 'MEDIUM' | 'LOW-MED' | 'LOW' | '—' {
 if (prob >= 0.9) return 'CRITICAL';
 if (prob >= 0.8) return 'HIGH';
 if (prob >= 0.7) return 'MEDIUM-HIGH';
 if (prob >= 0.5) return 'MEDIUM';
 if (prob >= 0.3) return 'LOW-MED';
 return 'LOW';
}

export function scheduleRender(): void {
 if (_renderScheduled) return;
 _renderScheduled = true;
 requestAnimationFrame(() => {
  _renderScheduled = false;
  if (_renderCallback) _renderCallback();
 });
}

export function setRenderCallback(cb: () => void): void { _renderCallback = cb; }

export function persistAlerts(alerts?: AlertPayload[]): void {
 const data = alerts ?? _allAlerts;
 try { sessionStorage.setItem(STORAGE_KEYS.ALERTS, JSON.stringify(data)); } catch { }
}

export function persistWindows(): void {
 try { sessionStorage.setItem(STORAGE_KEYS.WINDOWS, JSON.stringify(_windows)); } catch { }
}

export function persistHypotheses(): void {
 try { sessionStorage.setItem(STORAGE_KEYS.HYPOTHESES, JSON.stringify(_hypotheses)); } catch { }
}

export function persistSlice(): void {
 try { sessionStorage.setItem(STORAGE_KEYS.SLICE, JSON.stringify(_slice)); } catch { }
}

export function persistHyp(): void {
 try { sessionStorage.setItem(STORAGE_KEYS.SELECTED_HYP, JSON.stringify(_selectedHyp)); } catch { }
}

export function persistAgent2(): void {
 try { sessionStorage.setItem(STORAGE_KEYS.AGENT2_REPORTS, JSON.stringify(_agent2Reports)); } catch { }
}

export function loadPersistedState(): void {
 const savedWindows = sessionStorage.getItem(STORAGE_KEYS.WINDOWS);
 if (savedWindows) {
  try { _windows = JSON.parse(savedWindows); } catch { }
 }
 const savedHypotheses = sessionStorage.getItem(STORAGE_KEYS.HYPOTHESES);
 if (savedHypotheses) {
  try { _hypotheses = JSON.parse(savedHypotheses); } catch { }
 }
 const savedAlerts = sessionStorage.getItem(STORAGE_KEYS.ALERTS);
 if (savedAlerts) {
  try { _allAlerts = JSON.parse(savedAlerts); } catch { }
 }
 const savedSlice = sessionStorage.getItem(STORAGE_KEYS.SLICE);
 if (savedSlice) {
  try { _slice = JSON.parse(savedSlice); } catch { }
 }
 const savedSelectedHyp = sessionStorage.getItem(STORAGE_KEYS.SELECTED_HYP);
 if (savedSelectedHyp) {
  try { _selectedHyp = JSON.parse(savedSelectedHyp); } catch { }
 }
}

