export const APP_TEMPLATE = `
<div class="app-shell">

<!-- HEADER -->
<header class="header">
 <div class="header-row1">
  <div class="header-brand">
   <div class="brand-mark">CI</div>
   <div>
    <div class="brand-name">CISO Intelligence Dashboard</div>
    <div class="brand-sub">Evidence-Driven · Adaptive Windows · Hypothesis Graph</div>
   </div>
  </div>
  <div class="header-actions">
   <span id="footer-uptime" class="uptime-inline"></span>
   <button class="hdr-btn graph-toggle" id="btn-graph-toggle" title="Hypothesis Graph">🧬 Graph</button>
   <button class="hdr-btn finish-btn" id="btn-finish" title="Forçar conclusão de todas as janelas activas — gera log de classificações CISO para comparação académica">⏹ Finish</button>
   <div class="live-pill" id="footer-conn">
    <div class="live-dot"></div>
    <span>Connecting…</span>
   </div>
   <button class="hdr-btn danger" id="btn-clear-session" title="Reset session">↺</button>
   <button class="hdr-btn" id="debug-logs-btn" title="Download debug logs">📋</button>
  </div>
 </div>

 <!-- Slicer: ▼/▲ | data início | nav | track | data fim -->
 <!-- Slicer: botão toggle sozinho -->
 <div class="slice-toggle-row">
  <button class="slice-toggle-btn" id="btn-slice-toggle" title="Mostrar/ocultar detalhe stream" aria-expanded="true">▼</button>
  <span class="slice-toggle-label">(Para fins académicos)</span>
 </div>
 <!-- CONTEÚDO COLAPSÁVEL (todo o resto) -->
 <div class="slice-collapsible-content" id="slice-collapsible-content">
  <div class="slice-row" id="slice-row-main">
   <span id="dataset-bounds-start" class="dataset-bounds-ts">—</span>
   <div class="slice-nav-group">
    <button class="slice-nav-btn" id="btn-slice-reset"       title="Reset ao início">⏮</button>
    <button class="slice-nav-btn" id="btn-slice-back"        title="Recuar 5 min">◀</button>
    <button class="slice-nav-btn" id="btn-slice-forward"     title="Avançar 5 min">▶</button>
    <button class="slice-nav-btn" id="btn-slice-next-window" title="Ir para janela activa">⏭</button>
   </div>
   <div id="slice-track-wrap" class="slice-track-wrap">
    <div class="slice-track-bg"></div>
    <div class="slice-track-fill" id="slice-track-fill"></div>
    <div class="slice-today-marker" id="slice-today-marker" style="display:none"></div>
   </div>
   <span id="dataset-bounds-end" class="dataset-bounds-ts">—</span>
  </div>

  <div class="slice-stream-row" id="slice-stream-row">
   <span class="stream-tag now-tag">NOW</span>
   <span id="alert-progress" class="alert-progress">0/0</span>
   <span id="current-alert-timestamp" class="alert-timestamp">—</span>
   <span id="current-alert-details" class="alert-details">—</span>
   <span class="stream-vsep"></span>
   <span class="stream-tag next-tag">NEXT</span>
   <span id="next-alert-number" class="next-number">—</span>
   <span id="next-alert-timer" class="next-timer">—</span>
   <span id="next-alert-category" class="next-cat">—</span>
   <span id="next-alert-type" class="next-type">—</span>
   <span id="next-alert-time" class="next-time">—</span>
   <span class="stream-right-chips">
    <span id="stream-status" class="stream-status-chip">—</span>
   </span>
  </div>
 </div>  
 
 <!-- Timeline -->
 <div class="timeline-strip-panel" id="panel-timeline">
  <div class="timeline-strip-header">
   <span class="panel-title">📡 Timeline de Alertas</span>
   <span class="panel-badge" id="timeline-alert-count">0</span>
  </div>
    <div id="timeline-content" class="timeline-strip-scroll"></div>
  </div>
</header>

<!-- Hypothesis Graph overlay -->
<div class="graph-overlay" id="graph-overlay" style="display:none">
 <div class="graph-overlay-backdrop" id="graph-overlay-backdrop"></div>
 <div class="graph-overlay-panel">
  <div class="graph-overlay-header">
   <span class="panel-title">🧬 Hypothesis Graph — Global Memory</span>
   <div class="panel-legend">
    <span class="ldot" style="background:#38bdf8"></span>Auto
    <span class="ldot" style="background:#22c55e"></span>Confirmed
    <span class="ldot" style="background:#f97316"></span>Timeout
   </div>
   <button class="graph-close-btn" id="btn-graph-close">✕</button>
  </div>
  <div id="hypothesis-graph" class="graph-overlay-body"></div>
 </div>
</div>

<!-- MAIN — vertical scroll -->
<div class="main-stack">

 <!-- Parallel Windows -->
 <div class="windows-section" id="panel-windows">
  <div class="section-header">
   <span class="panel-title">📊 Parallel Windows</span>
   <span class="panel-badge" id="active-windows-badge">0 ativas</span>
   <div class="wm-filter-inline">
    <span class="wm-filter-label">Score ≥</span>
    <button class="wm-score-btn" onclick="window.__wmSetMinScore(Math.max(0,window.__wmMinScore|0-1))">−</button>
    <span class="wm-score-val" id="wm-score-display">0</span>
    <button class="wm-score-btn" onclick="window.__wmSetMinScore(Math.min(30,(window.__wmMinScore|0)+1))">+</button>
   </div>
   <button class="wm-mode-btn" id="btn-window-mode" title="Alternar modo de janela"
    onclick="window.__wmToggleMode(this)">📐 fixed</button>
   <div class="wm-sort-group">
    <span class="wm-filter-label">Ordem:</span>
    <button class="wm-sort-btn active" data-sort="score"
     onclick="window.__wmSetSort('score')" title="Por severidade">🔥 Score</button>
    <button class="wm-sort-btn" data-sort="time"
     onclick="window.__wmSetSort('time')" title="Mais recentes primeiro">🕒 Recente</button>
   </div>
   <div class="wm-risk-group">
    <span class="wm-filter-label">Risk:</span>
    <button class="wm-risk-btn" data-tier="CRITICAL"
     onclick="window.__wmToggleRisk('CRITICAL',this)">CR</button>
    <button class="wm-risk-btn" data-tier="HIGH"
     onclick="window.__wmToggleRisk('HIGH',this)">HI</button>
    <button class="wm-risk-btn" data-tier="MEDIUM-HIGH"
     onclick="window.__wmToggleRisk('MEDIUM-HIGH',this)">MH</button>
    <button class="wm-risk-btn" data-tier="MEDIUM"
     onclick="window.__wmToggleRisk('MEDIUM',this)">ME</button>
    <button class="wm-risk-btn" data-tier="LOW-MED"
     onclick="window.__wmToggleRisk('LOW-MED',this)">LM</button>
    <button class="wm-risk-btn" data-tier="LOW"
     onclick="window.__wmToggleRisk('LOW',this)">LO</button>
   </div>
   <div class="grid-picker">
    <span class="grid-label">Col:</span>
    <button class="grid-btn" data-cols="1" id="grid-btn-1">1</button>
    <button class="grid-btn" data-cols="2" id="grid-btn-2">2</button>
    <button class="grid-btn" data-cols="3" id="grid-btn-3">3</button>
    <button class="grid-btn active" data-cols="4" id="grid-btn-4">4</button>
   </div>
  </div>
  <div id="windows-panel" class="windows-grid-area"></div>
 </div>

 <!-- Intelligence Reports -->
 <div class="reports-section" id="panel-reports">
  <div class="section-header">
   <span class="panel-title">📋 Intelligence Reports</span>
   <span class="panel-badge" id="reports-count-badge">0</span>
   <span class="panel-badge pending-badge" id="reports-pending-badge" style="display:none" title="Relatórios em fila de processamento">⏳ <span id="reports-pending-count">0</span> em fila</span>
  </div>
  <div id="agent2-panel" class="reports-hscroll"></div>
 </div>

</div>

</div>
`;
