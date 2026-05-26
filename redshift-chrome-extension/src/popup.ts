interface TimeoutConfig {
llm_timeout: number;
api_timeout: number;
}

let timeoutConfig: TimeoutConfig = { llm_timeout: 120000, api_timeout: 120000 };

async function fetchTimeoutConfig(): Promise<void> {
try {
const resp = await fetch(`${getApiBase()}/api/config`);
const cfg = await resp.json();
if (cfg.llm_timeout_seconds) {
timeoutConfig.llm_timeout = cfg.llm_timeout_seconds * 1000;
}
if (cfg.api_timeout_seconds) {
timeoutConfig.api_timeout = cfg.api_timeout_seconds * 1000;
}
} catch {
}
}

interface CvssData {
score?: number; severity?: string; version?: string; vector?: string;
attack_vector?: string; privileges_required?: string;
}
interface CveData {
id?: string; published?: string; last_modified?: string;
description_en?: string; description_pt?: string;
cvss?: CvssData; affected_products?: string[];
references?: string[]; weaknesses?: string[];
}
interface CVEAnalysisResponse {
cve_id: string; cve_data: CveData; analysis: string; model_used: string;
}
interface SIEMAnalysisResponse { analysis: string; model_used: string; }

interface HealthResponse {
status:   string;
env:      string;
model:    string;
provider: string;
}

interface BackendConfig {
model:           string;
llm_provider:    string;     active_model:    string;     ollama_base_url: string;
default_window_days?:    number;
timeout_unit_minutes?:   number;
stream_timeout_minutes?: number;
stream_step_minutes?:    number;
}

interface StoredSession {
id: string; type: 'cve' | 'siem' | 'chat'; title: string;
severity?: string; model: string; timestamp: number; data: unknown;
}

interface WindowContext {
windowId:    string; label:       string; probability: number;
tier:        string; cves:        string[]; iocs:       string[];
phases:      string[]; assets:    string[]; receivedAt: number;
siemAlert?:  Record<string, unknown>;
}

const TIER_COLOR: Record<string, string> = {
  CRITICAL:      '#dc2626', HIGH: '#ea580c', 'MEDIUM-HIGH': '#d97706',
  MEDIUM:        '#ca8a04', 'LOW-MED': '#16a34a', LOW: '#0891b2',
};
interface AppSettings { apiUrl: string; defaultLevel: string; language: string; }

const DEFAULT_API_URL = 'http://localhost:8000'
let currentSettings: AppSettings = {
apiUrl: DEFAULT_API_URL, defaultLevel: 'intermediate', language: 'pt',
}
let sessionCounter  = 0
let chatHistory: { role: 'user' | 'assistant'; content: string }[] = []

let _backendConfig: BackendConfig | null = null

document.addEventListener('DOMContentLoaded', async () => {
await loadSettings()
setupTabs()
setupCvePanel()
setupSiemPanel()
setupChatPanel()
setupHistoryPanel()
setupSettingsPanel()
await checkBackendStatus()
consumePendingCve()
consumePendingWindowContext()
// Re-check for window context every 2s while popup is open
// (context may arrive after popup opens)
setInterval(consumePendingWindowContext, 2000)
setInterval(checkBackendStatus, 30_000)
})

function consumePendingCve(): void {
chrome.storage.local.get(['pendingCve'], (result) => {
const cve = result.pendingCve as string | undefined
if (!cve) return
chrome.storage.local.remove('pendingCve')
chrome.runtime.sendMessage({ type: 'CLEAR_BADGE' }).catch(() => {})
switchTab('cve')
const input = document.getElementById('cve-input') as HTMLInputElement
input.value = cve.replace(/^CVE-/i, '')
handleCveAnalyze()
})
}

function consumePendingWindowContext(force = false): void {
  chrome.storage.local.get(['pendingWindowContext'], (result) => {
    const ctx = result.pendingWindowContext as WindowContext | undefined
    if (!ctx) return
    if (Date.now() - ctx.receivedAt > 10 * 60 * 1000) {
      chrome.storage.local.remove('pendingWindowContext'); return
    }
    // force=true quando vem de click manual na timeline — substitui sempre
    if (!force && document.getElementById('soc-context-card')) return
    document.getElementById('soc-context-card')?.remove()  // ← remove o anterior
    chrome.storage.local.remove('pendingWindowContext')
    chrome.runtime.sendMessage({ type: 'CLEAR_BADGE' }).catch(() => {})
    renderWindowContext(ctx)
  })
}

// React immediately when storage changes (context pushed while popup is open)
chrome.storage.onChanged.addListener((changes, area) => {
if (area === 'local' && changes.pendingWindowContext?.newValue) {
  const ctx = changes.pendingWindowContext.newValue as WindowContext
  if (Date.now() - ctx.receivedAt <= 10 * 60 * 1000) {
    // Only auto-render if no card currently showing — don't disrupt active analysis
    if (!document.getElementById('soc-context-card')) {
      chrome.storage.local.remove('pendingWindowContext')
      consumePendingWindowContext(true)
    }
    // Otherwise leave in storage — will be shown when current card is closed
  }
}
})

function renderWindowContext(ctx: WindowContext): void {
document.getElementById('soc-context-card')?.remove()
const col  = TIER_COLOR[ctx.tier] || '#64748b'
const pct  = Math.round(ctx.probability * 100)
const age  = Math.round((Date.now() - ctx.receivedAt) / 1000)
const ageStr = age < 60 ? `${age}s` : `${Math.floor(age / 60)}m`
const escH = (s: string) => (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

// Inject styles if not already present
if (!document.getElementById('soc-ctx-style')) {
const style = document.createElement('style')
style.id = 'soc-ctx-style'
style.textContent = `
#soc-context-card{margin:6px 10px 0;background:#0d1a2b;border:1px solid rgba(56,189,248,.3);border-left:3px solid #38bdf8;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:10px;overflow:hidden;animation:soc-slide-in .2s ease}
@keyframes soc-slide-in{from{opacity:0;transform:translateY(-5px)}to{opacity:1;transform:translateY(0)}}
.soc-ctx-header{display:flex;align-items:center;gap:5px;padding:5px 8px;background:rgba(15,30,50,.6);border-bottom:1px solid rgba(56,189,248,.12)}
.soc-ctx-badge{font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px;border:1px solid;flex-shrink:0}
.soc-ctx-pct{font-weight:800;font-size:11px;flex-shrink:0}
.soc-ctx-label{flex:1;color:#e2e8f0;font-weight:600;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.soc-ctx-age{color:#64748b;font-size:9px;flex-shrink:0}
.soc-ctx-close{width:17px;height:17px;padding:0;background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);border-radius:3px;color:#fca5a5;font-size:10px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.soc-ctx-close:hover{background:rgba(239,68,68,.3)}
.soc-ctx-body{padding:5px 8px;display:flex;flex-direction:column;gap:4px}
.soc-ctx-row{display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.soc-ctx-lbl{color:#64748b;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;flex-shrink:0;min-width:34px}
.soc-chip{font-size:9px;font-weight:700;padding:2px 5px;border-radius:3px;border:1px solid}
.soc-chip.cve{background:rgba(232,25,44,.12);border-color:rgba(232,25,44,.35);color:#fca5a5;cursor:pointer}
.soc-chip.cve:hover{background:rgba(232,25,44,.25)}
.soc-chip.phase{background:rgba(56,189,248,.1);border-color:rgba(56,189,248,.3);color:#7dd3fc}
.soc-chip.empty{background:rgba(100,116,139,.1);border-color:rgba(100,116,139,.2);color:#64748b}
.soc-ctx-footer{padding:3px 8px;color:#475569;font-size:9px;border-top:1px solid rgba(56,189,248,.1);background:rgba(15,30,50,.3)}
.soc-ctx-footer code{background:rgba(56,189,248,.1);border-radius:2px;padding:0 3px;color:#38bdf8}
.soc-ctx-footer{display:flex;align-items:center;justify-content:space-between;gap:6px}
.soc-siem-btn{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;padding:2px 8px;border-radius:3px;background:rgba(56,189,248,.15);border:1px solid rgba(56,189,248,.4);color:#7dd3fc;cursor:pointer;white-space:nowrap}
.soc-siem-btn:hover{background:rgba(56,189,248,.28)}
`
document.head.appendChild(style)
}

const cveHtml = ctx.cves.length
  ? ctx.cves.slice(0,6).map(c =>
      `<span class="soc-chip cve" data-cve="${escH(c)}">${escH(c)} ▸</span>`
    ).join('')
  : '<span class="soc-chip empty">Sem CVEs detectados</span>'

const phaseHtml = ctx.phases.slice(0,4).map(p =>
  `<span class="soc-chip phase">${escH(p)}</span>`
).join('')

const siemBtn = ctx.siemAlert
  ? `<button class="soc-siem-btn" id="soc-siem-btn">📊 Analisar no SIEM</button>`
  : ''

const card = document.createElement('div')
card.id        = 'soc-context-card'
card.innerHTML = `
<div class="soc-ctx-header">
  <span class="soc-ctx-badge" style="border-color:${col}44;background:${col}18;color:${col}">${escH(ctx.tier)||'—'}</span>
  <span class="soc-ctx-pct" style="color:${col}">${pct}%</span>
  <span class="soc-ctx-label">${escH(ctx.label)}</span>
  <span class="soc-ctx-age">${ageStr} atrás</span>
  <button class="soc-ctx-close" id="soc-ctx-close-btn" title="Fechar">✕</button>
</div>
<div class="soc-ctx-body">
  ${ctx.phases.length ? `<div class="soc-ctx-row"><span class="soc-ctx-lbl">Fases</span>${phaseHtml}</div>` : ''}
  <div class="soc-ctx-row"><span class="soc-ctx-lbl">CVEs</span>${cveHtml}</div>
</div>
<div class="soc-ctx-footer">
  <span>Janela <code>${escH(ctx.windowId.slice(0,8))}</code> — clica num CVE</span>
  ${siemBtn}
</div>`

const tabs = document.querySelector('.tabs')
if (tabs) tabs.before(card)
else document.body.prepend(card)

// Wire close button — on close check for next pending context
document.getElementById('soc-ctx-close-btn')?.addEventListener('click', () => {
  card.remove()
  // Show next pending context if any
  setTimeout(consumePendingWindowContext, 300)
})

// Wire CVE chips
card.querySelectorAll<HTMLElement>('.soc-chip.cve').forEach(chip => {
  chip.style.cursor = 'pointer'
  chip.addEventListener('click', () => {
    const cveId = chip.dataset.cve || ''
    if (!cveId) return
    switchTab('cve')
    const input = document.getElementById('cve-input') as HTMLInputElement
    if (input) {
      input.value = cveId.replace(/^CVE-/i, '')
      handleCveAnalyze()
    }
  })
})

// Wire SIEM button — pre-fills SIEM tab with window context and triggers analysis
if (ctx.siemAlert) {
  document.getElementById('soc-siem-btn')?.addEventListener('click', () => {
    switchTab('siem')
    const textarea = document.getElementById('siem-input') as HTMLTextAreaElement
    if (textarea) {
      textarea.value = JSON.stringify(ctx.siemAlert, null, 2)
      const analyzeBtn = document.getElementById('siem-analyze-btn') as HTMLButtonElement
      analyzeBtn?.click()
    }
    card.remove()
  })
}
}

// ── Debug helper — accessible from popup DevTools console ────────────────
// Usage: __testSocCard()  (no window. prefix needed in popup context)
function __testSocCard(): void {
  renderWindowContext({
    windowId: 'test-window-abc123', label: 'Major Breach with Impact',
    probability: 0.92, tier: 'CRITICAL',
    cves: ['CVE-2024-12345', 'CVE-2023-44487'],
    iocs: ['192.168.1.100'], phases: ['RECON', 'EXFILTRATION'],
    assets: ['dc-ad01'], receivedAt: Date.now(),
    siemAlert: {
      'hypothesis': 'Major Breach with Impact', 'risk_tier': 'CRITICAL',
      'kill_chain': 'RECON → EXFILTRATION', 'alert_count': 12,
      'cves_detected': ['CVE-2024-12345'], 'source': 'SOC Dashboard',
    },
  })
}
// Expose on window for console access
Object.assign(window, { __testSocCard })

async function loadSettings(): Promise<void> {
return new Promise((resolve) => {
chrome.storage.local.get(['settings'], (result) => {
if (result.settings) currentSettings = { ...currentSettings, ...result.settings }
applySettingsToUI()
resolve()
})
})
}

function applySettingsToUI(): void {
const urlInput  = document.getElementById('setting-api-url')      as HTMLInputElement
const levelSel  = document.getElementById('setting-default-level') as HTMLSelectElement
const langSel   = document.getElementById('setting-lang')          as HTMLSelectElement
const levelMain = document.getElementById('detail-level')          as HTMLSelectElement
if (urlInput)  urlInput.value  = currentSettings.apiUrl
if (levelSel)  levelSel.value  = currentSettings.defaultLevel
if (langSel)   langSel.value   = currentSettings.language
if (levelMain) levelMain.value = currentSettings.defaultLevel
}

async function saveSettings(): Promise<void> {
return new Promise((resolve) => {
chrome.storage.local.set({ settings: currentSettings }, resolve)
})
}

function getApiBase(): string { return currentSettings.apiUrl.replace(/\/$/, '') }

function setupTabs(): void {
document.querySelectorAll<HTMLButtonElement>('.tab-btn').forEach((btn) => {
btn.addEventListener('click', () => switchTab(btn.dataset.tab!))
})
}

function switchTab(tab: string): void {
document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'))
document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'))
document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active')
document.getElementById(`panel-${tab}`)?.classList.add('active')
if (tab === 'history') renderHistory()
if (tab === 'settings' && _backendConfig) applyBackendConfigToSettings(_backendConfig)
}

async function checkBackendStatus(): Promise<void> {
const dot         = document.getElementById('status-dot')!
const text        = document.getElementById('status-text')!
const footerDot   = document.getElementById('footer-model-dot')!
const footerLabel = document.getElementById('footer-model-label')!

dot.className    = 'status-dot checking'
text.textContent = 'A verificar…'

try {
 const resp = await fetch(`${getApiBase()}/health`, {
signal: AbortSignal.timeout(4000),
})
if (!resp.ok) throw new Error('HTTP ' + resp.status)
const data: HealthResponse = await resp.json()

dot.className              = 'status-dot online'
text.textContent           = 'Online'
footerDot.style.background = '#22c55e'

 const modelLabel = data.model || ''
// Show interim label — fetchBackendConfig will update with definitive value
footerLabel.textContent = modelLabel ? `Modelo: ${modelLabel}` : 'Modelo: A carregar...'

 fetchBackendConfig().catch(() => {
 // fetchBackendConfig failed — use /health model or fallback
 applyModelToSettings(modelLabel || 'LLM activo', data.provider || '')
 if (!modelLabel) footerLabel.textContent = 'Modelo: LLM activo'
})

} catch {
dot.className              = 'status-dot offline'
text.textContent           = 'Offline'
footerDot.style.background = '#ef4444'
footerLabel.textContent    = 'Backend offline'
 applyModelToSettings('Backend offline', '')
}
}

async function fetchBackendConfig(): Promise<void> {
const resp = await fetch(`${getApiBase()}/api/config`, {
signal: AbortSignal.timeout(4000),
})
if (!resp.ok) throw new Error('HTTP ' + resp.status)
const cfg: BackendConfig = await resp.json()
_backendConfig = cfg

const footerLabel = document.getElementById('footer-model-label')
const model = cfg.model || cfg.active_model || ''
if (footerLabel) footerLabel.textContent = model ? `Modelo: ${model}` : 'Modelo: LLM activo'

applyBackendConfigToSettings(cfg)
}

function applyBackendConfigToSettings(cfg: BackendConfig): void {
applyModelToSettings(
cfg.active_model || cfg.model || '—',
cfg.llm_provider || '—',
)
}

function applyModelToSettings(modelStr: string, providerStr: string): void {
const modelDisplay    = document.getElementById('setting-model-display')    as HTMLInputElement | null
const providerDisplay = document.getElementById('setting-provider-display') as HTMLInputElement | null
if (modelDisplay)    modelDisplay.value    = modelStr
if (providerDisplay) providerDisplay.value = providerStr
}

function setupCvePanel(): void {
const input      = document.getElementById('cve-input')   as HTMLInputElement
const analyzeBtn = document.getElementById('analyze-btn') as HTMLButtonElement
analyzeBtn.addEventListener('click', handleCveAnalyze)
input.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleCveAnalyze() })
input.addEventListener('input', () => {
input.value = input.value.toUpperCase().replace(/^CVE-/, '').replace(/[^0-9-]/g, '')
})
}

async function handleCveAnalyze(): Promise<void> {
const input      = document.getElementById('cve-input')   as HTMLInputElement
const analyzeBtn = document.getElementById('analyze-btn') as HTMLButtonElement
const levelSel   = document.getElementById('detail-level') as HTMLSelectElement

const rawVal = input.value.trim().toUpperCase()
const cveId  = rawVal.startsWith('CVE-') ? rawVal : `CVE-${rawVal}`
if (!/^CVE-\d{4}-\d{4,}$/.test(cveId)) {
showCveError('Formato inválido. Exemplo: <code>2026-5167</code>')
return
}

analyzeBtn.disabled = true
showCveLoading(true)
clearCveResult()

try {
const data = await fetchCveAnalysis(cveId, levelSel.value)
renderCveResult(data)
await saveSession({
id: genSessionId(), type: 'cve', title: cveId,
severity: data.cve_data?.cvss?.severity ?? 'unknown',
model: data.model_used, timestamp: Date.now(), data,
})
updateFooterSession()
} catch (err) {
showCveError(`Erro ao analisar: ${(err as Error).message}`)
} finally {
showCveLoading(false)
analyzeBtn.disabled = false
}
}

async function fetchCveAnalysis(cveId: string, level: string): Promise<CVEAnalysisResponse> {
const resp = await fetch(
`${getApiBase()}/api/v1/cve/${cveId}/analyze?level=${level}`,
{ signal: AbortSignal.timeout(timeoutConfig.llm_timeout) },
)
if (!resp.ok) {
const err = await resp.json().catch(() => ({})) as { detail?: string }
throw new Error(err.detail ?? `HTTP ${resp.status}`)
}
return resp.json() as Promise<CVEAnalysisResponse>
}

function showCveLoading(show: boolean): void {
const el = document.getElementById('cve-loading')!
el.className = 'loading-state' + (show ? ' visible' : '')
if (show) {
const steps = ['step-1','step-2','step-3','step-4']
steps.forEach((id, i) => {
const s = document.getElementById(id)!
s.className = 'loading-step'
setTimeout(() => {
 s.classList.add('show')
 if (i > 0) document.getElementById(steps[i - 1])!.classList.add('done')
}, i * 900)
})
}
}

function clearCveResult(): void { document.getElementById('cve-result')!.innerHTML = '' }

function showCveError(msg: string): void {
document.getElementById('cve-result')!.innerHTML =
`<div class="error-msg"><div class="error-icon">⚠️</div><div>${msg}</div></div>`
}

function renderCveResult(data: CVEAnalysisResponse): void {
const resultDiv = document.getElementById('cve-result')!
const cvss      = data.cve_data?.cvss
const score     = cvss?.score    ?? 'N/A'
const severity  = (cvss?.severity ?? 'unknown').toLowerCase()

const footerLabel = document.getElementById('footer-model-label')
if (footerLabel) footerLabel.textContent = `Modelo: ${data.model_used}`
updateFooterSession()

const sections   = parseAnalysisSections(data.analysis)
const published  = data.cve_data?.published
? new Date(data.cve_data.published).toLocaleDateString('pt-PT') : '—'
const vector     = cvss?.attack_vector ?? cvss?.vector?.split(':')[1]?.split('/')[0] ?? '—'
const weaknesses = data.cve_data?.weaknesses?.join(', ') ?? '—'

resultDiv.innerHTML = `
<div class="cve-card">
<div class="cve-card-header">
 <div class="cve-id">${data.cve_id}</div>
 <div class="cvss-badge sev-${severity}">
 CVSS ${score} &nbsp; ${(cvss?.severity ?? '—').toUpperCase()}
 </div>
</div>
<div class="cve-meta">
 <div class="meta-chip">
 <span class="meta-chip-label">Vetor:</span>
 <span class="meta-chip-value">${vector}</span>
 </div>
 <div class="meta-chip">
 <span class="meta-chip-label">CWE:</span>
 <span class="meta-chip-value">${weaknesses}</span>
 </div>
 <div class="meta-chip">
 <span class="meta-chip-label">Publicado:</span>
 <span class="meta-chip-value">${published}</span>
 </div>
</div>
<div class="analysis-sections">${sections}</div>
<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);
  font-family:var(--mono);font-size:10px;color:var(--text3)">
 Modelo: ${escapeHtml(data.model_used)}
</div>
<div class="card-actions">
 <button class="action-btn" onclick="copyAnalysis()">📋 Copiar</button>
 <button class="action-btn" onclick="sendToChatFromCVE('${data.cve_id}')">💬 Chat</button>
 <button class="action-btn danger"
 onclick="document.getElementById('cve-result').innerHTML=''">✕ Limpar</button>
</div>
</div>`

;(window as unknown as Record<string, unknown>)._lastAnalysis = data.analysis
;(window as unknown as Record<string, unknown>)._lastCveId    = data.cve_id
}

function parseAnalysisSections(analysis: string): string {
const lines = analysis.split('\n')
let html = '', inSection = false, currentTitle = '', currentBody = ''

const flushSection = () => {
if (!currentTitle) return
const bodyHtml  = formatBodyText(currentBody.trim())
const mitreHtml = extractMitreTags(currentBody)
html += `<div class="section-block">
<div class="section-title">${currentTitle}</div>
<div class="section-body">${mitreHtml || bodyHtml}</div>
</div>`
currentTitle = ''; currentBody = ''
}

for (const line of lines) {
const h2 = line.match(/^## (.+)$/)
if (h2) { flushSection(); inSection = true; currentTitle = h2[1].trim() }
else if (inSection) { currentBody += line + '\n' }
}
flushSection()

return html || `<div class="section-block">
<div class="section-title">Análise</div>
<div class="section-body">${formatBodyText(analysis)}</div>
</div>`
}

function formatBodyText(text: string): string {
return text.split('\n').filter(l => l.trim())
.map(line => {
const li = line.match(/^[-*] (.+)$/)
return li ? `<li>${escapeHtml(li[1])}</li>` : `<p>${escapeHtml(line.trim())}</p>`
})
.join('')
.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>')
}

function extractMitreTags(text: string): string {
const tagRegex = /\bT\d{4}(?:\.\d{3})?\b/g
const tags     = [...new Set(text.match(tagRegex) ?? [])]
if (!tags.length) return ''
const body    = formatBodyText(text.replace(tagRegex, (t) => `<code>${t}</code>`))
const tagHtml = tags.map(t =>
`<a class="mitre-tag"
 href="https://attack.mitre.org/techniques/${t.replace('.', '/')}/"
 target="_blank">${t}</a>`,
).join('')
return body + `<div class="mitre-tags">${tagHtml}</div>`
}

function escapeHtml(str: string): string {
return str
.replace(/&/g,  '&amp;')
.replace(/</g,  '&lt;')
.replace(/>/g,  '&gt;')
.replace(/`([^`]+)`/g,       '<code>$1</code>')
.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
}

;(window as any).copyAnalysis = function (): void {
const analysis = (window as unknown as Record<string, unknown>)._lastAnalysis as string
if (!analysis) return
navigator.clipboard.writeText(analysis).then(() =>
showToast('Copiado para a área de transferência!'),
)
}

;(window as any).sendToChatFromCVE = function (cveId: string): void {
const chatInput = document.getElementById('chat-input') as HTMLInputElement
chatInput.value = `Aprofunda a análise da ${cveId}`
switchTab('chat')
chatInput.focus()
}

const MOCK_SIEM_ALERT = {
'@timestamp': '2026-03-09T10:23:00.000Z', 'event.kind': 'alert',
'event.category': 'intrusion_detection',
'rule.name': 'Possible CVE-2026-5167 Exploitation Attempt',
'rule.severity': 'high', 'host.name': 'workstation-042', 'host.ip': '192.168.1.42',
'user.name': 'jdoe', 'process.name': 'OUTLOOK.EXE', 'process.pid': 4928,
'network.direction': 'outbound', 'destination.ip': '203.0.113.99',
'destination.port': 445,
'signal.reason': 'Suspicious outbound SMB connection from Outlook process',
}

function setupSiemPanel(): void {
document.getElementById('mock-btn')!.addEventListener('click', () => {
;(document.getElementById('siem-input') as HTMLTextAreaElement).value =
JSON.stringify(MOCK_SIEM_ALERT, null, 2)
})
;(document.getElementById('siem-analyze-btn') as HTMLButtonElement)
.addEventListener('click', handleSiemAnalyze)
}

async function handleSiemAnalyze(): Promise<void> {
const textarea   = document.getElementById('siem-input')       as HTMLTextAreaElement
const analyzeBtn = document.getElementById('siem-analyze-btn') as HTMLButtonElement
const resultDiv  = document.getElementById('siem-result')!
const loadingEl  = document.getElementById('siem-loading')!

const raw = textarea.value.trim()
if (!raw) { showToast('Insere um alerta JSON do SIEM.'); return }

let alertJson: Record<string, unknown>
try { alertJson = JSON.parse(raw) }
catch { showToast('JSON inválido. Verifica o formato.'); return }

analyzeBtn.disabled         = true
loadingEl.className         = 'loading-state visible'
resultDiv.style.display     = 'none'

const steps = ['siem-step-1','siem-step-2','siem-step-3']
steps.forEach((id, i) => {
const s = document.getElementById(id)!
s.className = 'loading-step'
setTimeout(() => s.classList.add('show'), i * 1000)
})

try {
const resp = await fetch(`${getApiBase()}/api/v1/siem/analyze`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ alert: alertJson, detail_level: 'intermediate' }),
signal: AbortSignal.timeout(timeoutConfig.llm_timeout),
})
if (!resp.ok) {
const err = await resp.json().catch(() => ({})) as { detail?: string }
throw new Error(err.detail ?? `HTTP ${resp.status}`)
}
const data: SIEMAnalysisResponse = await resp.json()

loadingEl.className     = 'loading-state'
resultDiv.style.display = 'block'

const alertName = String(alertJson['rule.name'] ?? alertJson['event.action'] ?? 'Alerta SIEM')
const severity  = String(alertJson['rule.severity'] ?? alertJson['event.severity'] ?? 'unknown')

resultDiv.innerHTML = `
<div class="result-scroll">
 <div class="siem-result">
 <div class="siem-alert-header">
 <div class="siem-alert-icon">⚡</div>
 <div>
 <div class="siem-alert-title">${escapeHtml(alertName)}</div>
 <div class="siem-alert-sub">
  severity: ${severity.toUpperCase()} ·
  host: ${escapeHtml(String(alertJson['host.name'] ?? '—'))}
 </div>
 </div>
 </div>
 <div class="analysis-sections">${parseAnalysisSections(data.analysis)}</div>
 <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);
  font-family:var(--mono);font-size:10px;color:var(--text3)">
 Modelo: ${escapeHtml(data.model_used)}
 </div>
 </div>
</div>`

await saveSession({
id: genSessionId(), type: 'siem', title: alertName,
severity, model: data.model_used, timestamp: Date.now(), data,
})
updateFooterSession()

} catch (err) {
loadingEl.className     = 'loading-state'
resultDiv.style.display = 'block'
resultDiv.innerHTML = `
<div style="padding:14px">
 <div class="error-msg">
 <div class="error-icon">⚠️</div>
 <div>${(err as Error).message}</div>
 </div>
</div>`
} finally {
analyzeBtn.disabled = false
}
}

const CHAT_SYSTEM_PROMPT =
'És um analista sénior de cibersegurança da equipa RedShift. ' +
'Respondes a perguntas sobre CVEs, alertas SIEM, MITRE ATT&CK, técnicas de ataque e defesa. ' +
'Sê preciso, técnico mas acessível. Responde sempre em Português de Portugal. ' +
'Usa formatação markdown simples quando relevante.'

function setupChatPanel(): void {
const sendBtn   = document.getElementById('chat-send')!
const chatInput = document.getElementById('chat-input') as HTMLInputElement
sendBtn.addEventListener('click', handleChatSend)
chatInput.addEventListener('keydown', (e) => {
if (e.key === 'Enter' && !e.shiftKey) handleChatSend()
})
}

async function handleChatSend(): Promise<void> {
const chatInput = document.getElementById('chat-input') as HTMLInputElement
const sendBtn   = document.getElementById('chat-send') as HTMLButtonElement
const msg       = chatInput.value.trim()
if (!msg) return

chatInput.value  = ''
sendBtn.disabled = true
appendChatMsg('user', msg)
chatHistory.push({ role: 'user', content: msg })

const typingId = appendChatTyping()

try {
const resp = await fetch(`${getApiBase()}/api/v1/analysis/chat`, {
method:  'POST',
headers: { 'Content-Type': 'application/json' },
body:    JSON.stringify({
 messages: [
 { role: 'system', content: CHAT_SYSTEM_PROMPT },
 ...chatHistory.slice(-10),
 ],
 max_tokens: 800,
}),
signal: AbortSignal.timeout(timeoutConfig.llm_timeout),
})
removeTyping(typingId)

if (!resp.ok) {
const fallback = await chatFallback(msg)
appendChatMsg('agent', fallback)
chatHistory.push({ role: 'assistant', content: fallback })
} else {
const data = await resp.json() as { reply?: string; analysis?: string; model_used?: string }
const reply = data.reply ?? data.analysis ?? 'Sem resposta.'
appendChatMsg('agent', reply)
chatHistory.push({ role: 'assistant', content: reply })
 if (data.model_used && data.model_used !== 'none') {
 const footerLabel = document.getElementById('footer-model-label')
 if (footerLabel) footerLabel.textContent = `Modelo: ${data.model_used}`
}
}
} catch {
removeTyping(typingId)
appendChatMsg('agent',
`Não consegui conectar ao servidor. Verifica se o backend está a correr em \`${getApiBase()}\`.`,
)
} finally {
sendBtn.disabled = false
chatInput.focus()
}
}

async function chatFallback(userMsg: string): Promise<string> {
const cveMatch = userMsg.match(/CVE-\d{4}-\d{4,}/i)
if (cveMatch) {
try {
const data = await fetchCveAnalysis(cveMatch[0].toUpperCase(), 'intermediate')
return (
 `**${data.cve_id}** (CVSS ${data.cve_data?.cvss?.score ?? '—'} ` +
 `${data.cve_data?.cvss?.severity ?? ''})\n\n${data.analysis}`
)
} catch {  }
}
return (
'Não consegui obter uma resposta. ' +
'Certifica-te que o backend está online e que `LLM_PROVIDER` está definido no `.env`.'
)
}

function appendChatMsg(role: 'user' | 'agent', text: string): void {
const container = document.getElementById('chat-messages')!
const time      = new Date().toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
const avatar    = role === 'user'
? `<div class="msg-avatar" style="font-family:var(--mono);font-weight:700;font-size:11px;background:var(--red);color:#fff">TU</div>`
: `<div class="msg-avatar">🤖</div>`
const bubbleHtml = role === 'agent' ? formatBodyText(text) : escapeHtml(text)
const div        = document.createElement('div')
div.className    = `msg ${role}`
div.innerHTML    = `${avatar}<div>
<div class="msg-bubble">${bubbleHtml}</div>
<div class="msg-time">${time}</div>
</div>`
container.appendChild(div)
container.scrollTop = container.scrollHeight
}

function appendChatTyping(): string {
const id        = 'typing-' + Date.now()
const container = document.getElementById('chat-messages')!
const div       = document.createElement('div')
div.id          = id
div.className   = 'msg agent'
div.innerHTML   = `<div class="msg-avatar">🤖</div>
<div class="msg-bubble" style="display:flex;gap:5px;align-items:center;padding:12px 14px">
<span style="animation:blink 0.8s 0s infinite;opacity:0.6">●</span>
<span style="animation:blink 0.8s 0.25s infinite;opacity:0.6">●</span>
<span style="animation:blink 0.8s 0.5s infinite;opacity:0.6">●</span>
</div>`
container.appendChild(div)
container.scrollTop = container.scrollHeight
if (!document.getElementById('blink-style')) {
const style       = document.createElement('style')
style.id          = 'blink-style'
style.textContent = '@keyframes blink {0%,100%{opacity:0.2} 50%{opacity:1}}'
document.head.appendChild(style)
}
return id
}

function removeTyping(id: string): void { document.getElementById(id)?.remove() }

function setupHistoryPanel(): void {
document.getElementById('clear-history')!.addEventListener('click', async () => {
if (confirm('Apagar todo o histórico de sessões?')) { await clearHistory(); renderHistory() }
})
}

async function saveSession(session: StoredSession): Promise<void> {
return new Promise((resolve) => {
chrome.storage.local.get(['sessions'], (result) => {
const sessions: StoredSession[] = result.sessions ?? []
sessions.unshift(session)
chrome.storage.local.set({ sessions: sessions.slice(0, 50) }, resolve)
})
})
}

async function clearHistory(): Promise<void> {
return new Promise((resolve) => { chrome.storage.local.remove('sessions', resolve) })
}

function renderHistory(): void {
const listEl  = document.getElementById('history-list')!
const countEl = document.getElementById('history-count')!
chrome.storage.local.get(['sessions'], (result) => {
const sessions: StoredSession[] = result.sessions ?? []
const n = sessions.length
countEl.textContent = `${n} sessão${n !== 1 ? 'ões' : ''} guardada${n !== 1 ? 's' : ''}`
if (!n) {
listEl.innerHTML = '<div class="history-empty">Nenhuma análise guardada ainda.</div>'
return
}
const sevColor: Record<string, string> = {
critical: '#fca5a5', high: '#fdba74', medium: '#fde68a', low: '#86efac',
}
listEl.innerHTML = sessions.map((s) => {
const date = new Date(s.timestamp).toLocaleString('pt-PT', {
 day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
})
const icon = s.type === 'cve' ? '🔍' : s.type === 'siem' ? '📊' : '💬'
const sev  = (s.severity ?? '').toLowerCase()
const col  = sevColor[sev] ?? 'var(--text3)'
return `<div class="history-item" onclick="replaySession('${s.id}')">
 <div class="history-icon">${icon}</div>
 <div class="history-info">
 <div class="history-title">${escapeHtml(s.title)}</div>
 <div class="history-meta">
 <span class="history-date">${date}</span>
 <span class="history-model">${escapeHtml(s.model)}</span>
 </div>
 </div>
 ${s.severity ? `<div class="history-sev" style="color:${col}">${sev.toUpperCase()}</div>` : ''}
</div>`
}).join('')
})
}

;(window as any).replaySession = function (id: string): void {
chrome.storage.local.get(['sessions'], (result) => {
const sessions: StoredSession[] = result.sessions ?? []
const session = sessions.find((s) => s.id === id)
if (!session) return
if (session.type === 'cve') {
switchTab('cve')
;(document.getElementById('cve-input') as HTMLInputElement).value =
 session.title.replace('CVE-', '')
renderCveResult(session.data as CVEAnalysisResponse)
} else if (session.type === 'siem') {
switchTab('siem')
}
})
}

function setupSettingsPanel(): void {
document.getElementById('save-settings-btn')!.addEventListener('click', async () => {
const apiUrl = (document.getElementById('setting-api-url')      as HTMLInputElement).value.trim()
const level  = (document.getElementById('setting-default-level') as HTMLSelectElement).value
const lang   = (document.getElementById('setting-lang')          as HTMLSelectElement).value
if (!apiUrl) { showToast('Introduz uma URL válida.'); return }
currentSettings = { apiUrl, defaultLevel: level, language: lang }
await saveSettings()
await checkBackendStatus()
showToast('Definições guardadas!')
})
}

function genSessionId(): string { return Math.random().toString(36).slice(2, 10) }

function updateFooterSession(): void {
const el = document.getElementById('footer-session') as HTMLElement | null
if (el) el.textContent = `sessão #${++sessionCounter}`
}

let toastTimer: ReturnType<typeof setTimeout>
function showToast(msg: string): void {
const toast = document.getElementById('toast')!
toast.textContent = msg
toast.classList.add('show')
clearTimeout(toastTimer)
toastTimer = setTimeout(() => toast.classList.remove('show'), 2500)
}