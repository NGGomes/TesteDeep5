import './slice.css';
import { getSlice, setSlice, persistSlice, scheduleRender, getWindows } from '../core/store';
import { fmtDateTimeSeconds } from '../core/utils';

// ── Module state ──────────────────────────────────────────────────────────────
let _datasetStartMs: number = 0;
let _datasetEndMs:   number = 0;
let _seekStartMs:    number = 0;   
let _seekEndMs:      number = 0;   
let _isDragging:     'start' | 'end' | null = null;

let _countdownInterval: ReturnType<typeof setInterval> | null = null;
let _isCountdownRunning = false;

let _speedFactor: number = 0.05;

// Callback fired when the analyst commits a seek (mouseup / touchend)
// Implemented in main.ts — resets all current data and restarts streaming
let _onSeekCommit: ((startMs: number, endMs: number) => void) | null = null;

export function setOnSeekCommit(fn: (startMs: number, endMs: number) => void): void {
 _onSeekCommit = fn;
}

// ── Speed factor ──────────────────────────────────────────────────────────────
export function setSpeedFactor(factor: number): void {
 _speedFactor = factor;
}

const MAX_COUNTDOWN_SECONDS = 5;

export function calculateSimulatedSeconds(realGapMs: number): number {
 const sim = Math.max(1, Math.ceil((realGapMs / 1000) * _speedFactor));
 return Math.min(sim, MAX_COUNTDOWN_SECONDS);
}

// ── Alert display ─────────────────────────────────────────────────────────────
function esc(s: string): string {
 return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

export function updateCurrentAlertDisplay(
 alertNumber: string, category: string, type: string,
 timestampMs: number, currentIndex: number, total: number
): void {
 const el = document.getElementById('current-alert-details');
 const ts = document.getElementById('current-alert-timestamp');
 const pg = document.getElementById('alert-progress');
 if (el) el.innerHTML = `<strong>${esc(alertNumber)}</strong> ${esc(category)} / ${esc(type)}`;
 if (ts && timestampMs) ts.innerHTML = fmtDateTimeSeconds(timestampMs);
 if (pg) pg.innerHTML = `${currentIndex + 1}/${total}`;
}

export function updateNextAlertInfo(
 nextNumber: string, nextCategory: string, nextType: string,
 nextTimestampMs: number, _gapReal: number, _gapSim: number
): void {
 const num  = document.getElementById('next-alert-number');
 const cat  = document.getElementById('next-alert-category');
 const typ  = document.getElementById('next-alert-type');
 const time = document.getElementById('next-alert-time');
 if (num)  num.innerHTML  = esc(nextNumber);
 if (cat)  cat.innerHTML  = esc(nextCategory);
 if (typ)  typ.innerHTML  = esc(nextType);
 if (time && nextTimestampMs)
  time.innerHTML = new Date(nextTimestampMs).toLocaleTimeString('pt-PT');
}

export function updateNextAlertTimer(seconds: number): void {
 const el = document.getElementById('next-alert-timer');
 if (!el) return;
 const m = Math.floor(seconds / 60);
 const s = seconds % 60;
 el.innerHTML = `${m}:${s.toString().padStart(2, '0')}`;
 el.classList.toggle('timer-critical', seconds > 0 && seconds <= 5);
}

// ── Countdown ─────────────────────────────────────────────────────────────────
export function startCountdown(seconds: number, _alertInfo: any, onComplete: () => void): void {
 if (_isCountdownRunning) return;
 if (_countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
 _isCountdownRunning = true;
 let remaining = seconds;
 updateNextAlertTimer(remaining);
 _countdownInterval = setInterval(() => {
  remaining--;
  updateNextAlertTimer(Math.max(0, remaining));
  if (remaining <= 0) {
   clearInterval(_countdownInterval!); _countdownInterval = null;
   if (_isCountdownRunning) { _isCountdownRunning = false; onComplete(); }
  }
 }, 1000);
}

export function stopCountdown(): void {
 if (_countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
 _isCountdownRunning = false;
 updateNextAlertTimer(0);
}

// ── Dataset bounds ────────────────────────────────────────────────────────────
export function setDatasetBounds(startMs: number, endMs: number): void {
 _datasetStartMs = startMs;
 _datasetEndMs   = endMs;
 if (!_seekStartMs) _seekStartMs = startMs;
 if (!_seekEndMs)   _seekEndMs   = endMs;
 _repaintTrack();
 _updateBoundsLabel();
 const slice = getSlice();
 if (slice.dataMinMs !== startMs || slice.dataMaxMs !== endMs) {
  setSlice({ ...slice, dataMinMs: startMs, dataMaxMs: endMs });
  persistSlice(); scheduleRender();
 }
}

function _updateBoundsLabel(): void {
 // New layout: start and end are separate spans flanking the track
 const elStart = document.getElementById('dataset-bounds-start');
 const elEnd   = document.getElementById('dataset-bounds-end');
 // Legacy: dataset-bounds-label (keep for compatibility)
 const elOld   = document.getElementById('dataset-bounds-label');

 const fmt = (ms: number) => ms
  ? new Date(ms).toLocaleString('pt-PT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
   })
  : '—';

 if (elStart) elStart.textContent = fmt(_datasetStartMs);
 if (elEnd)   elEnd.textContent   = fmt(_datasetEndMs);
 if (elOld)   elOld.textContent   = `📅 ${fmt(_datasetStartMs)} → ${fmt(_datasetEndMs)}`;
}

// ── Track repaint ─────────────────────────────────────────────────────────────
function _pct(ms: number): number {
 if (!_datasetStartMs || _datasetEndMs <= _datasetStartMs) return 0;
 return Math.max(0, Math.min(100,
  ((ms - _datasetStartMs) / (_datasetEndMs - _datasetStartMs)) * 100
 ));
}

function _repaintTrack(): void {
 const fill  = document.getElementById('slice-track-fill');
 const hS    = document.getElementById('slice-handle-start') as HTMLElement | null;
 const hE    = document.getElementById('slice-handle-end')   as HTMLElement | null;
 const lS    = document.getElementById('slice-label-start')  as HTMLElement | null;
 const lE    = document.getElementById('slice-label-end')    as HTMLElement | null;

 const startMs = _seekStartMs || _datasetStartMs;
 const endMs   = _seekEndMs   || _datasetEndMs;

 const pS = _pct(startMs);
 const pE = _pct(endMs);

 if (fill) { fill.style.left = pS + '%'; fill.style.width = (pE - pS) + '%'; }

 if (hS) hS.style.left = pS + '%';
 if (hE) hE.style.left = pE + '%';

 // Labels on the handles — show timestamp
 const fmtShort = (ms: number) => ms
  ? new Date(ms).toLocaleString('pt-PT', {
    day:'2-digit', month:'2-digit', year:'numeric',
    hour:'2-digit', minute:'2-digit', second:'2-digit'
   })
  : '—';

 if (lS) lS.textContent = fmtShort(startMs);
 if (lE) lE.textContent = fmtShort(endMs);
}

// ── Sync slice inputs (called by main.ts renderFull) ──────────────────────────
export function syncSliceInputs(dataMinMs: number, dataMaxMs: number, windowStartMs: number): void {
 const eMin = _datasetStartMs || dataMinMs;
 const eMax = _datasetEndMs   || dataMaxMs;
 if (eMin >= eMax) return;
 if (!_seekStartMs) _seekStartMs = Math.max(eMin, Math.min(eMax, windowStartMs));
 if (!_seekEndMs)   _seekEndMs   = eMax;
 _repaintTrack();
}

export function updateSliceLabels(_windowStartMs: number, _windowEndMs: number): void {
 // Labels are now embedded in the handles — nothing to do here.
 // Kept for API compatibility with main.ts.
}

// ── Wire controls ─────────────────────────────────────────────────────────────
export function wireSliceControls(): void {
 const track = document.getElementById('slice-track-wrap');
 if (!track) return;

 _ensureHandles(track);

 // ── Toggle ▼/▲ — show/hide stream detail row ──────────────────────────────
 const toggleBtn  = document.getElementById('btn-slice-toggle');
 const collapsibleContent = document.getElementById('slice-collapsible-content');
 let   _expanded  = true;

 toggleBtn?.addEventListener('click', () => {
  _expanded = !_expanded;

  if (collapsibleContent) {
    collapsibleContent.classList.toggle('hidden', !_expanded);
  }
  
  if (toggleBtn) {
   toggleBtn.textContent   = _expanded ? '▼' : '▶';
   toggleBtn.title         = _expanded ? 'Ocultar detalhe stream' : 'Mostrar detalhe stream';
   toggleBtn.classList.toggle('collapsed', !_expanded);
  }
 });

 const hS = document.getElementById('slice-handle-start')!;
 const hE = document.getElementById('slice-handle-end')!;

 // ── Drag logic (mouse + touch) ──────────────────────────────────────────────
 function _msFromClientX(clientX: number): number {
  const rect  = track!.getBoundingClientRect();
  const pct   = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  return _datasetStartMs + pct * (_datasetEndMs - _datasetStartMs);
 }

 function _onMove(clientX: number): void {
  if (!_isDragging || !_datasetStartMs) return;
  const ms = _msFromClientX(clientX);
  const STEP = 60_000; // 1-minute snap
  const snapped = Math.round(ms / STEP) * STEP;

  if (_isDragging === 'start') {
   _seekStartMs = Math.max(_datasetStartMs, Math.min(_seekEndMs - STEP, snapped));
  } else {
   _seekEndMs = Math.min(_datasetEndMs, Math.max(_seekStartMs + STEP, snapped));
  }
  _repaintTrack();
 }

 function _onUp(): void {
  if (!_isDragging) return;
  _isDragging = null;
  // Commit the seek — main.ts will reset current data and restart streaming
  if (_onSeekCommit && _seekStartMs && _seekEndMs) {
   _onSeekCommit(_seekStartMs, _seekEndMs);
  }
 }

 // Mouse
 hS.addEventListener('mousedown', (e) => { e.preventDefault(); _isDragging = 'start'; });
 hE.addEventListener('mousedown', (e) => { e.preventDefault(); _isDragging = 'end'; });
 window.addEventListener('mousemove', (e) => _onMove(e.clientX));
 window.addEventListener('mouseup',   _onUp);

 // Touch
 hS.addEventListener('touchstart', (e) => { e.preventDefault(); _isDragging = 'start'; }, { passive: false });
 hE.addEventListener('touchstart', (e) => { e.preventDefault(); _isDragging = 'end'; },   { passive: false });
 window.addEventListener('touchmove', (e) => _onMove(e.touches[0].clientX), { passive: true });
 window.addEventListener('touchend',  _onUp);

 // ── Nav buttons ─────────────────────────────────────────────────────────────
 const STEP_MS = 5 * 60_000; // 5-minute step

 function _shift(deltaMs: number): void {
  if (!_datasetStartMs) return;
  const span  = _seekEndMs - _seekStartMs;
  const newS  = Math.max(_datasetStartMs, Math.min(_datasetEndMs - span, _seekStartMs + deltaMs));
  _seekStartMs = newS;
  _seekEndMs   = Math.min(_datasetEndMs, newS + span);
  _repaintTrack();
  if (_onSeekCommit) _onSeekCommit(_seekStartMs, _seekEndMs);
 }

 document.getElementById('btn-slice-reset')?.addEventListener('click', () => {
  if (!_datasetStartMs) return;
  _seekStartMs = _datasetStartMs;
  _seekEndMs   = _datasetEndMs;
  _repaintTrack();
  if (_onSeekCommit) _onSeekCommit(_seekStartMs, _seekEndMs);
 });

 document.getElementById('btn-slice-back')?.addEventListener('click', () => _shift(-STEP_MS));
 document.getElementById('btn-slice-forward')?.addEventListener('click', () => _shift(+STEP_MS));

 document.getElementById('btn-slice-next-window')?.addEventListener('click', () => {
  const wins = getWindows().filter(w => !w.isClosed).sort((a, b) => a.createdAt - b.createdAt);
  if (!wins.length || !_datasetStartMs) return;
  const wStart = wins[0].createdAt;
  const span   = _seekEndMs - _seekStartMs;
  _seekStartMs = Math.max(_datasetStartMs, Math.min(_datasetEndMs - span, wStart));
  _seekEndMs   = Math.min(_datasetEndMs, _seekStartMs + span);
  _repaintTrack();
  if (_onSeekCommit) _onSeekCommit(_seekStartMs, _seekEndMs);
 });
}

// ── Handle injection ──────────────────────────────────────────────────────────
function _ensureHandles(track: HTMLElement): void {
 if (document.getElementById('slice-handle-start')) return; // already injected

 const css = `
  position:absolute;top:50%;transform:translate(-50%,-50%);
  width:10px;height:12px;border-radius:2px;
  background:var(--cyan-hi,#22d3ee);border:2px solid #0f172a;
  cursor:ew-resize;z-index:10;user-select:none;touch-action:none;
  display:flex;align-items:flex-end;justify-content:center;
  box-shadow:0 0 0 2px rgba(34,211,238,.4);
 `;
 const lblCss = `
  position:absolute;top:100%;margin-top:3px;left:50%;
  transform:translateX(-50%);white-space:nowrap;
  font-family:monospace;font-size:9px;color:var(--cyan-hi,#22d3ee);
  background:rgba(15,23,42,.85);padding:0px 2px;border-radius:2px;
  pointer-events:none;
 `;

 const hS = document.createElement('div');
 hS.id = 'slice-handle-start';
 hS.style.cssText = css + 'background:linear-gradient(180deg,#22d3ee,#0891b2);';
 hS.innerHTML = `<span id="slice-label-start" style="${lblCss}"></span>`;

 const hE = document.createElement('div');
 hE.id = 'slice-handle-end';
 hE.style.cssText = css + 'background:linear-gradient(180deg,#818cf8,#4f46e5);';
 hE.innerHTML = `<span id="slice-label-end" style="${lblCss}"></span>`;

 track.appendChild(hS);
 track.appendChild(hE);
}

export function getSeekRange(): { startMs: number; endMs: number } {
 return { startMs: _seekStartMs || _datasetStartMs, endMs: _seekEndMs || _datasetEndMs };
}
