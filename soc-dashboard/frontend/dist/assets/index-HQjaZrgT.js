var ls=Object.defineProperty;var ds=(e,t,s)=>t in e?ls(e,t,{enumerable:!0,configurable:!0,writable:!0,value:s}):e[t]=s;var fe=(e,t,s)=>ds(e,typeof t!="symbol"?t+"":t,s);(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const o of document.querySelectorAll('link[rel="modulepreload"]'))n(o);new MutationObserver(o=>{for(const a of o)if(a.type==="childList")for(const d of a.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&n(d)}).observe(document,{childList:!0,subtree:!0});function s(o){const a={};return o.integrity&&(a.integrity=o.integrity),o.referrerPolicy&&(a.referrerPolicy=o.referrerPolicy),o.crossOrigin==="use-credentials"?a.credentials="include":o.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function n(o){if(o.ep)return;o.ep=!0;const a=s(o);fetch(o.href,a)}})();const ps=`
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
`,Pe={RECON:"#38bdf8",INITIAL_ACCESS:"#bef264",EXECUTION:"#f97316",LATERAL_MOVEMENT:"#e879f9",PERSISTENCE:"#67e9f9",EXFILTRATION:"#f472b6",IMPACT:"#ef4444"},He={RECON:"Re",INITIAL_ACCESS:"In",EXECUTION:"Ex",LATERAL_MOVEMENT:"La",PERSISTENCE:"Pe",EXFILTRATION:"Ef",IMPACT:"Ac"},V={ALERTS:"ciso_alerts",TRIGGER_META:"ciso_trigger_meta",AGENT2_REPORTS:"ciso_agent2_reports",SLICE:"ciso_slice",SELECTED_HYP:"ciso_selected_hyp",TIMELINE_MONTH:"ciso_timeline_month",TOTAL_RECEIVED:"ciso_total_received",CONNECTION:"ciso_connection",WINDOWS:"ciso_windows",HYPOTHESES:"ciso_hypotheses",GRAPH_STATE:"ciso_graph_state",ACTIVE_WINDOWS:"ciso_active_windows"},ms=15,us={"Ransomware & Digital Extortion":{icon:"🔴",short:"Ransomware"},"Data Exfiltration & Corporate Espionage":{icon:"🟠",short:"Exfiltration"},"Advanced Persistent Threats (APT)":{icon:"🟡",short:"APT"},"Credential & Identity Compromise":{icon:"🔵",short:"Credential"},"Destructive Operations & Wipeware":{icon:"💀",short:"Destructive"},"Supply Chain & Third-Party Compromise":{icon:"📦",short:"Supply Chain"},"Critical Service Disruption — DDoS":{icon:"🌊",short:"DDoS"},"Social Engineering, Phishing & BEC":{icon:"🎣",short:"Phishing"},"System & Application Vulnerability Exploitation":{icon:"🐛",short:"Exploit"},"Insider Threats & Physical Security Breaches":{icon:"👤",short:"Insider"},"Regulatory & Compliance Violations":{icon:"⚖️",short:"Compliance"},"Reconnaissance & Pre-Attack Intelligence Gathering":{icon:"🔍",short:"Recon"},"Operational Noise":{icon:"📡",short:"Noise"},Other:{icon:"❓",short:"Other"},"Major Breach":{icon:"🔴",short:"Major Breach"},"Major Breach with Impact":{icon:"🔴",short:"Major Breach"},"Critical Combined Attack":{icon:"🔴",short:"Critical"}};function Be(e){if(!e)return"⚠️ Unknown";const t=us[e];if(t)return`${t.icon} ${t.short}`;const s=e.toLowerCase();return s.includes("ransomware")||s.includes("ransom")?"🔴 Ransomware":s.includes("exfiltration")||s.includes("data leak")||s.includes("data breach")?"🟠 Exfiltration":s.includes("apt")||s.includes("advanced persistent")?"🟡 APT":s.includes("credential")||s.includes("identity")?"🔵 Credential":s.includes("destructive")||s.includes("wiper")||s.includes("wipeware")?"💀 Destructive":s.includes("supply chain")||s.includes("third-party")?"📦 Supply Chain":s.includes("ddos")||s.includes("disruption")?"🌊 DDoS":s.includes("phishing")||s.includes("bec")||s.includes("social engineering")?"🎣 Phishing":s.includes("vulnerability")||s.includes("exploit")||s.includes("cve")?"🐛 Exploit":s.includes("insider")||s.includes("privileged")?"👤 Insider":s.includes("compliance")||s.includes("regulatory")||s.includes("nis2")||s.includes("gdpr")?"⚖️ Compliance":s.includes("recon")||s.includes("reconnaissance")||s.includes("scanning")?"🔍 Recon":s.includes("major breach")||s.includes("critical combined")?"🔴 Major Breach":e.split(" ").slice(0,2).join(" ").slice(0,15)||e.slice(0,15)}let we=[],Se=[],I=[],Je=0,Vt="connecting",qt=0,Ye=[],Ge={dataMinMs:Date.now()-7*24*60*60*1e3,dataMaxMs:Date.now(),windowStartMs:Date.now()-ms*60*1e3,windowEndMs:Date.now()},gs=new Map,Ue=!1,Ve=null;function Kt(){return we}function fs(){return I}function hs(){return Vt}function Yt(){return qt}function Qe(){return Ye}function _s(){return{...Ge}}function ws(e){we=e}function Ht(e){Vt=e}function vs(e){qt=e}function Qt(e){Ye=e}function ys(e){Ge={...e}}function bs(e){const t=gs.get(String(e.number));t&&(e={...e,...t}),we.push(e),we.length>5e3&&we.shift()}function xs(e){const t=I.findIndex(s=>s.windowId===e.windowId);t>=0?I[t]=e:I.push(e),I.sort((s,n)=>n.createdAt-s.createdAt),I.length>50&&(I=I.slice(0,50)),tt(),Ze()}function $s(e,t){const s=I.findIndex(n=>n.windowId===e);s>=0&&(I[s].alerts.find(o=>o.number===t.number)||(I[s].alerts.push(t),tt(),Ze(),et()))}function Zt(e,t){const s=I.findIndex(n=>n.windowId===e);s>=0&&!I[s].isClosed&&(I[s].isClosed=!0,I[s].closeReason=t,t==="validation"&&(I[s].isConfirmed=!0,I[s].confirmedAt=Date.now()),tt(),Ze(),et())}function Ze(){Se=I.filter(t=>!t.isClosed).map(t=>({id:t.windowId,windowStart:t.createdAt,windowEnd:t.expiresAt,tier:Es(t.probability),category:t.hypothesisLabel,mitreTechs:[],evidenceCount:t.alerts.length,evidenceGap:0,isSevere:t.probability>.7,enisaDecision:t.probability>.7?"Severe Incident":"Operational Noise",sources:["SIEM","EDR"],killChains:t.phases.length,execAction:"Under investigation",nis2:"Monitor",gdpr:"Monitor",alerts:t.alerts,anomalyScore:t.probability,reportText:"",detectedThreatType:t.hypothesisLabel,cisoState:t.probability>.85?"CRITICAL_COMBINED_ATTACK":t.probability>.7?"INCIDENTE_GRAVE":"ATIVIDADE_SUSPEITA",phaseScore:t.phaseScore,phasesDetected:t.phases,triggerTypes:["alert"],discardedCount:0,discardReasons:[],windowId:t.windowId,expiresAt:t.expiresAt,isClosed:t.isClosed})),Je>=Se.length&&Se.length>0&&(Je=0),Is()}function Es(e){return e>=.9?"CRITICAL":e>=.8?"HIGH":e>=.7?"MEDIUM-HIGH":e>=.5?"MEDIUM":e>=.3?"LOW-MED":"LOW"}function et(){Ue||(Ue=!0,requestAnimationFrame(()=>{Ue=!1,Ve&&Ve()}))}function Ss(e){Ve=e}function tt(){try{sessionStorage.setItem(V.WINDOWS,JSON.stringify(I))}catch{}}function Is(){try{sessionStorage.setItem(V.HYPOTHESES,JSON.stringify(Se))}catch{}}function Ts(){try{sessionStorage.setItem(V.SLICE,JSON.stringify(Ge))}catch{}}function es(){try{sessionStorage.setItem(V.AGENT2_REPORTS,JSON.stringify(Ye))}catch{}}function Cs(){const e=sessionStorage.getItem(V.WINDOWS);if(e)try{I=JSON.parse(e)}catch{}const t=sessionStorage.getItem(V.HYPOTHESES);if(t)try{Se=JSON.parse(t)}catch{}const s=sessionStorage.getItem(V.ALERTS);if(s)try{we=JSON.parse(s)}catch{}const n=sessionStorage.getItem(V.SLICE);if(n)try{Ge=JSON.parse(n)}catch{}const o=sessionStorage.getItem(V.SELECTED_HYP);if(o)try{Je=JSON.parse(o)}catch{}}function g(e){return e?e.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"):""}function Ms(e){return e?new Date(e).toLocaleString("pt-PT",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"}):"—"}const ts={};function ks(e){var t,s,n;return((t=e.metadata)==null?void 0:t.window_id)||((s=e.metadata)==null?void 0:s.output_timestamp)||((n=e.metadata)==null?void 0:n.generated_at)||JSON.stringify(e.metadata).slice(0,32)}function As(e){var t,s,n,o;return((t=e.metadata)==null?void 0:t.selected_hypothesis)||((n=(s=e.decision)==null?void 0:s.selected_hypothesis)==null?void 0:n.label)||((o=e.ciso_report)==null?void 0:o.primary_hypothesis)||"—"}function Ls(e){var t,s,n;return((t=e.ciso_report)==null?void 0:t.top_risk_tier)||((n=(s=e.decision)==null?void 0:s.selected_hypothesis)==null?void 0:n.risk_tier)||""}function Ns(e){return e==="CRITICAL"?"#dc2626":e==="HIGH"?"#ea580c":e==="MEDIUM-HIGH"?"#d97706":e==="MEDIUM"?"#ca8a04":"#64748b"}function Os(e){var d,l,p,_;function t(i,r){const c=i?i.split("/").pop().split("\\").pop():"",h=r?r.split("/").pop().split("\\").pop():"",u=c||(h?h.replace(".pdf",".tex"):"");return u?{pdf:`/render-pdf?file=${encodeURIComponent(u)}`,tex:c?`/reports/agent2/${encodeURIComponent(c)}`:null}:{pdf:null,tex:null}}const s=((d=e.metadata)==null?void 0:d.tex_file)||((l=e.metadata)==null?void 0:l.source_report)||"",n=((p=e.metadata)==null?void 0:p.pdf_file)||"",o=((_=e.metadata)==null?void 0:_.soc_tex_file)||s.replace("_ciso.tex","_soc.tex");return{ciso:t(s,n),soc:t(o,"")}}function Ds(e){var t,s,n,o;return!!(((t=e.metadata)==null?void 0:t.confirmed)===!0||(s=e.metadata)!=null&&s.confirmation_method||(o=(n=e.decision)==null?void 0:n.selected_hypothesis)!=null&&o.label)}const st=new Map;function Rs(){let e=document.getElementById("r2-modal-root");return e||(e=document.createElement("div"),e.id="r2-modal-root",document.body.appendChild(e)),e}function Ps(e,t){let s=0,n=0;t.style.cursor="grab",t.addEventListener("mousedown",o=>{o.preventDefault(),s=o.clientX-e.offsetLeft,n=o.clientY-e.offsetTop,t.style.cursor="grabbing";const a=l=>{const p=Math.max(0,Math.min(window.innerWidth-e.offsetWidth,l.clientX-s)),_=Math.max(0,Math.min(window.innerHeight-e.offsetHeight,l.clientY-n));e.style.left=p+"px",e.style.top=_+"px"},d=()=>{t.style.cursor="grab",window.removeEventListener("mousemove",a),window.removeEventListener("mouseup",d)};window.addEventListener("mousemove",a),window.addEventListener("mouseup",d)})}window.__r2openmode=e=>{const t=e.dataset.rid||"",s=e.dataset.mode||"ciso";!t||!st.get(t)||window.__r2open(t,s)};window.__r2open=(e,t)=>{var T;const s=st.get(e);if(!s)return;const{cisoHtml:n,socHtml:o,cisoPdf:a,cisoTex:d,socPdf:l,socTex:p,col:_,label:i,tier:r,methodIcon:c,method:h}=s,u=t||s.mode||"ciso",m=Be(i);(T=document.getElementById(`r2-modal-${CSS.escape(e)}`))==null||T.remove();const f=document.createElement("div");f.className="r2-modal",f.id=`r2-modal-${e}`,f.dataset.modalId=e,f.style.cssText=`left:${Math.max(20,(window.innerWidth-520)/2)}px;top:${Math.max(20,(window.innerHeight-600)/2)}px`;const b=r?`<span class="r2-tier" style="color:${_};border-color:${_}44;background:${_}14">${g(r)}</span>`:"",v=u==="ciso"?a:l,M=u==="ciso"?d:p;f.innerHTML=`
  <div class="r2-modal-handle">
   <div class="r2-modal-title">
    ${b}
    <span class="r2-modal-label">${g(m)}</span>
   </div>
   <div class="r2-modal-meta">
    <span class="r2-confirm-badge">${c} ${g(h)}</span>
   </div>
   <button class="r2-modal-close" onclick="this.closest('.r2-modal')?.remove()" title="Fechar">✕</button>
  </div>
  <div class="r2-modal-body">
   <div class="r2-tabs" style="margin-bottom:8px">
    <button class="r2-tab ${u==="ciso"?"active":""}"
     onclick="window.__r2modaltab(this,'ciso')">CISO</button>
    <button class="r2-tab ${u==="soc"?"active":""}"
     onclick="window.__r2modaltab(this,'soc')">SOC</button>
   </div>
   <div class="r2-modal-content" style="${u==="ciso"?"":"display:none"}">${n}</div>
   <div class="r2-modal-content" style="${u==="soc"?"":"display:none"}">${o}</div>
   <div class="r2-actions r2-modal-actions"
     style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border2)"
     data-ciso-pdf="${g(a)}" data-ciso-tex="${g(d)}"
     data-soc-pdf="${g(l)}"   data-soc-tex="${g(p)}">
    ${v?`<a class="r2-btn r2-btn-pdf" href="${g(v)}" target="_blank">📄 PDF</a>`:'<span class="r2-btn r2-btn-disabled">📄 PDF</span>'}
    ${M?`<a class="r2-btn r2-btn-tex" href="${g(M)}" target="_blank">{} .tex</a>`:'<span class="r2-btn r2-btn-disabled">{} .tex</span>'}
   </div>
  </div>`,Rs().appendChild(f),Ps(f,f.querySelector(".r2-modal-handle"))};window.__r2modaltab=(e,t)=>{const s=e.closest(".r2-modal");if(!s)return;s.querySelectorAll(".r2-tab").forEach(l=>l.classList.remove("active")),e.classList.add("active"),s.querySelectorAll(".r2-modal-content").forEach((l,p)=>{l.style.display=p===0&&t==="ciso"||p===1&&t==="soc"?"":"none"});const o=s.querySelector(".r2-modal-actions");if(!o)return;const a=o.dataset[t==="ciso"?"cisoPdf":"socPdf"]||"",d=o.dataset[t==="ciso"?"cisoTex":"socTex"]||"";o.innerHTML=(a?`<a class="r2-btn r2-btn-pdf" href="${g(a)}" target="_blank">📄 PDF</a>`:'<span class="r2-btn r2-btn-disabled">📄 PDF</span>')+(d?`<a class="r2-btn r2-btn-tex" href="${g(d)}" target="_blank">{} .tex</a>`:'<span class="r2-btn r2-btn-disabled">{} .tex</span>')};window.__r2toggle=(e,t)=>{};function Hs(e,t,s,n){const o=(s||[]).filter(Ds);return o.length===0?`<div class="r2-empty">
   <span style="font-size:20px;opacity:.35">📋</span>
   <span>Sem relatórios confirmados ainda.</span>
  </div>`:o.map(a=>{var nt,it,ot,at,rt,ct,lt,dt,pt,mt,ut,gt,ft,ht,_t,wt,vt,yt,bt,xt,$t,Et,St,It,Tt,Ct,Mt,kt,At,Lt,Nt,Ot,Dt;const d=ks(a),l=As(a),p=Be(l),_=Ls(a),i=Ns(_),r=ts[d]||"ciso",c=Os(a),h=((nt=a.metadata)==null?void 0:nt.output_timestamp)||((it=a.metadata)==null?void 0:it.generated_at)||"",u=h?new Date(h).toLocaleString("pt-PT",{dateStyle:"short",timeStyle:"short"}):"—",m=((ot=a.metadata)==null?void 0:ot.confirmation_method)||"auto",f=m.includes("operator")?"operator":m.includes("timeout")?"timeout":"auto",b=f==="operator"?"✋":f==="timeout"?"⏱":"⚡",v=(at=a.metadata)!=null&&at.llm_used?`<span class="r2-badge llm">🤖 ${g(((rt=a.metadata)==null?void 0:rt.model_used)||"LLM")}</span>`:'<span class="r2-badge rule">⚡ Rule</span>',M=(lt=(ct=a.decision)==null?void 0:ct.selected_hypothesis)==null?void 0:lt.probability,T=M!=null?`${Math.round(M*100)}%`:"",G=((dt=a.ciso_report)==null?void 0:dt.executive_summary)||((pt=a.ciso_report)==null?void 0:pt.summary)||a.executive_summary||"—",L=(((mt=a.ciso_report)==null?void 0:mt.top_categories)||((ut=a.top_hypotheses)==null?void 0:ut.map(E=>[E.label||E.category,E.confidence||E.probability]))||[]).slice(0,3),z=((gt=a.ciso_report)==null?void 0:gt.business_impact)||"",y=((ft=a.ciso_report)==null?void 0:ft.regulatory_implications)||"",$=(((ht=a.ciso_report)==null?void 0:ht.strategic_recommendations)||[]).slice(0,4),O=((_t=a.soc_report)==null?void 0:_t.total_alerts)??"—",B=(((wt=a.soc_report)==null?void 0:wt.affected_assets)||[]).slice(0,4),q=((yt=(vt=a.soc_report)==null?void 0:vt.ioc_bundle)==null?void 0:yt.cve_ids)||((bt=a.soc_report)==null?void 0:bt.detected_cves)||[],se=(((xt=a.soc_report)==null?void 0:xt.mitre_techniques)||[]).slice(0,5),F=(($t=a.soc_report)==null?void 0:$t.kill_chain_phases)||[],U=(((Et=a.soc_report)==null?void 0:Et.remediation_steps)||[]).slice(0,4),ce=(((It=(St=a.soc_report)==null?void 0:St.ioc_bundle)==null?void 0:It.ipv4_addresses)||[]).slice(0,4),le=(((Ct=(Tt=a.soc_report)==null?void 0:Tt.ioc_bundle)==null?void 0:Ct.fqdns)||[]).slice(0,4),de=(((Mt=a.soc_report)==null?void 0:Mt.timeline)||[]).slice(0,5),x=`
   <div class="r2-section-lbl">Executive Summary</div>
   <div class="r2-summary">${g(G)}</div>

   ${L.length?`
   <div class="r2-section-lbl">Top Hipóteses</div>
   <div class="r2-cats">
    ${L.map(([E,ye])=>`
     <div class="r2-cat-row">
      <span class="r2-cat-name">${g(String(E))}</span>
      <div class="r2-cat-bar-wrap">
       <div class="r2-cat-bar" style="width:${Math.round(Number(ye)*100)}%"></div>
      </div>
      <span class="r2-cat-pct">${Math.round(Number(ye)*100)}%</span>
     </div>`).join("")}
   </div>`:""}

   ${z?`
   <div class="r2-section-lbl">Impacto no Negócio</div>
   <div class="r2-text">${g(z)}</div>`:""}

   ${y?`
   <div class="r2-section-lbl">Implicações Regulatórias</div>
   <div class="r2-text r2-text-warn">${g(y)}</div>`:""}

   ${$.length?`
   <div class="r2-section-lbl">Recomendações</div>
   <ol class="r2-list">
    ${$.map(E=>`<li>${g(E)}</li>`).join("")}
   </ol>`:""}`,A=`
   <div class="r2-kv-grid">
    <div class="r2-kv"><span class="r2-k">Alertas</span><span class="r2-v">${O}</span></div>
    ${F.length?`<div class="r2-kv"><span class="r2-k">Kill-Chain</span><span class="r2-v">${g(F.join(" → "))}</span></div>`:""}
   </div>

   ${B.length?`
   <div class="r2-section-lbl">Assets Afectados</div>
   <div class="r2-tags">${B.map(E=>`<span class="r2-tag">${g(E)}</span>`).join("")}</div>`:""}

   ${se.length?`
   <div class="r2-section-lbl">MITRE ATT&CK</div>
   <div class="r2-tags">${se.map(E=>`<span class="r2-tag mitre">${g(E)}</span>`).join("")}</div>`:""}

   ${q.length?`
   <div class="r2-section-lbl">CVEs</div>
   <div class="r2-tags">${q.slice(0,5).map(E=>`<span class="r2-tag cve">${g(E)}</span>`).join("")}</div>`:""}

   ${ce.length||le.length?`
   <div class="r2-section-lbl">IoCs</div>
   <div class="r2-tags">
    ${ce.map(E=>`<span class="r2-tag ioc">${g(E)}</span>`).join("")}
    ${le.map(E=>`<span class="r2-tag ioc">${g(E)}</span>`).join("")}
   </div>`:""}

   ${de.length?`
   <div class="r2-section-lbl">Timeline</div>
   <div class="r2-timeline">
    ${de.map(E=>`
     <div class="r2-tl-row">
      <span class="r2-tl-ts">${g(E.timestamp)}</span>
      <span class="r2-tl-ev">${g(E.event)}</span>
     </div>`).join("")}
   </div>`:""}

   ${U.length?`
   <div class="r2-section-lbl">Remediação</div>
   <ol class="r2-list">
    ${U.map(E=>`<li>${g(E)}</li>`).join("")}
   </ol>`:""}`;st.set(d,{cisoHtml:x,socHtml:A,mode:r,cisoPdf:c.ciso.pdf||"",cisoTex:c.ciso.tex||"",socPdf:c.soc.pdf||"",socTex:c.soc.tex||"",col:i,label:l,tier:_,methodIcon:b,method:f});const D=(()=>{var Rt,Pt;const E=((Rt=a.soc_report)==null?void 0:Rt.trigger_events)||[];if(E.length>0)return E.map(Q=>Q.id).filter(Q=>Q&&Q!=="—").join(", ");const ye=((Pt=a.soc_report)==null?void 0:Pt.raw_alerts)||[];return ye.length>0?ye.map(Q=>Q.Number||Q.number||"").filter(Q=>Q).join(", "):""})(),R=((kt=a.metadata)==null?void 0:kt.window_id)||"",W=((At=a.metadata)==null?void 0:At.alert_count)||0,P=((Lt=a.metadata)==null?void 0:Lt.phases)||[],X=((Nt=a.metadata)==null?void 0:Nt.phase_score)||0,K=(Ot=a.metadata)!=null&&Ot.window_start_ms?new Date(a.metadata.window_start_ms).toLocaleTimeString("pt-PT").slice(0,5):"",Y=(Dt=a.metadata)!=null&&Dt.window_end_ms?new Date(a.metadata.window_end_ms).toLocaleTimeString("pt-PT").slice(0,5):"",Fe=W||R?`
 <div class="r2-window-ctx">
  ${R?`<span class="r2-wid" title="Window ID">${g(R.slice(0,8))}</span>`:""}
  ${W?`<span class="r2-meta-chip">📊 ${W} alertas</span>`:""}
  ${X?`<span class="r2-meta-chip">🎯 Score: ${X}</span>`:""}
  ${P.length?`<span class="r2-meta-chip">🔗 ${P.slice(0,3).join(" → ")}</span>`:""}
  ${K?`<span class="r2-meta-chip">📅 ${K}${Y?` → ${Y}`:""}</span>`:""}
 </div>`:"",cs=D?`
<div class="r2-alert-numbers" style="margin-top:6px;padding-top:4px;border-top:1px solid var(--border2);">
  <span style="font-size:8px;font-family:var(--mono);color:var(--text4);">📋 Alertas:</span>
  <span style="font-size:8px;font-family:var(--mono);color:var(--cyan-hi);
               word-break:break-all;white-space:normal;display:block;margin-top:2px;">
    ${g(D)}
  </span>
</div>`:"";return`
<div class="r2-card" data-report-id="${g(d)}" style="border-left-color:${i}">
    <div class="r2-label-row">
        ${_?`<span class="r2-tier" style="color:${i};border-color:${i}44;background:${i}14">${g(_)}</span>`:""}
        ${T?`<span class="r2-prob" style="color:${i};font-weight:800;font-size:11px">${T}</span>`:""}
        <span class="r2-hyp" title="${g(l)}">${g(p)}</span>
        <button class="r2-toggle-btn" title="Abrir relatório completo" onclick="window.__r2open('${g(d)}')">⊞</button>
    </div>
    <div class="r2-meta-row" style="margin-top:5px">
        <span class="r2-confirm-badge">${b} ${g(f)}</span>
        ${v}
    </div>
    ${Fe}
    ${cs}
    <div class="r2-ts" style="margin-top:4px">${u}</div>
</div>`}).join("")}function Bs(){window.__r2tab=(e,t)=>{ts[e]=t}}function Ws(e){const t={connecting:{text:"Connecting…",color:"#d97706",animate:!0},connected:{text:"Live",color:"#16a34a",animate:!0},reconnecting:{text:"Reconnecting…",color:"#ea580c",animate:!0},done:{text:"Processing complete",color:"#7c3aed",animate:!1},error:{text:"Connection error",color:"#dc2626",animate:!1}},s=t[e]??t.connecting;return`${s.animate?`<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${s.color};animation:livepulse 2s ease-in-out infinite;margin-right:5px"></span>`:`<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${s.color};margin-right:5px"></span>`}<span>${s.text}</span>`}let C=0,j=0,k=0,N=0,ne=null,te=null,xe=!1,ss=.05,Z=null;function js(e){Z=e}function zs(e){ss=e}const Gs=5;function Bt(e){const t=Math.max(1,Math.ceil(e/1e3*ss));return Math.min(t,Gs)}function ve(e){return(e||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function Wt(e,t,s,n,o,a){const d=document.getElementById("current-alert-details"),l=document.getElementById("current-alert-timestamp"),p=document.getElementById("alert-progress");d&&(d.innerHTML=`<strong>${ve(e)}</strong> ${ve(t)} / ${ve(s)}`),l&&n&&(l.innerHTML=Ms(n)),p&&(p.innerHTML=`${o+1}/${a}`)}function jt(e,t,s,n,o,a){const d=document.getElementById("next-alert-number"),l=document.getElementById("next-alert-category"),p=document.getElementById("next-alert-type"),_=document.getElementById("next-alert-time");d&&(d.innerHTML=ve(e)),l&&(l.innerHTML=ve(t)),p&&(p.innerHTML=ve(s)),_&&n&&(_.innerHTML=new Date(n).toLocaleTimeString("pt-PT"))}function pe(e){const t=document.getElementById("next-alert-timer");if(!t)return;const s=Math.floor(e/60),n=e%60;t.innerHTML=`${s}:${n.toString().padStart(2,"0")}`,t.classList.toggle("timer-critical",e>0&&e<=5)}function Fs(e,t,s){if(xe)return;te&&(clearInterval(te),te=null),xe=!0;let n=e;pe(n),te=setInterval(()=>{n--,pe(Math.max(0,n)),n<=0&&(clearInterval(te),te=null,xe&&(xe=!1,s()))},1e3)}function Le(){te&&(clearInterval(te),te=null),xe=!1,pe(0)}function Us(e,t){C=e,j=t,k||(k=e),N||(N=t),$e(),Xs();const s=_s();(s.dataMinMs!==e||s.dataMaxMs!==t)&&(ys({...s,dataMinMs:e,dataMaxMs:t}),Ts(),et())}function Xs(){const e=document.getElementById("dataset-bounds-start"),t=document.getElementById("dataset-bounds-end"),s=document.getElementById("dataset-bounds-label"),n=o=>o?new Date(o).toLocaleString("pt-PT",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"}):"—";e&&(e.textContent=n(C)),t&&(t.textContent=n(j)),s&&(s.textContent=`📅 ${n(C)} → ${n(j)}`)}function zt(e){return!C||j<=C?0:Math.max(0,Math.min(100,(e-C)/(j-C)*100))}function $e(){const e=document.getElementById("slice-track-fill"),t=document.getElementById("slice-handle-start"),s=document.getElementById("slice-handle-end"),n=document.getElementById("slice-label-start"),o=document.getElementById("slice-label-end"),a=k||C,d=N||j,l=zt(a),p=zt(d);e&&(e.style.left=l+"%",e.style.width=p-l+"%"),t&&(t.style.left=l+"%"),s&&(s.style.left=p+"%");const _=i=>i?new Date(i).toLocaleString("pt-PT",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"}):"—";n&&(n.textContent=_(a)),o&&(o.textContent=_(d))}function Js(){var i,r,c,h;const e=document.getElementById("slice-track-wrap");if(!e)return;Vs(e);const t=document.getElementById("btn-slice-toggle"),s=document.getElementById("slice-collapsible-content");let n=!0;t==null||t.addEventListener("click",()=>{n=!n,s&&s.classList.toggle("hidden",!n),t&&(t.textContent=n?"▼":"▶",t.title=n?"Ocultar detalhe stream":"Mostrar detalhe stream",t.classList.toggle("collapsed",!n))});const o=document.getElementById("slice-handle-start"),a=document.getElementById("slice-handle-end");function d(u){const m=e.getBoundingClientRect(),f=Math.max(0,Math.min(1,(u-m.left)/m.width));return C+f*(j-C)}function l(u){if(!ne||!C)return;const m=d(u),f=6e4,b=Math.round(m/f)*f;ne==="start"?k=Math.max(C,Math.min(N-f,b)):N=Math.min(j,Math.max(k+f,b)),$e()}function p(){ne&&(ne=null,Z&&k&&N&&Z(k,N))}o.addEventListener("mousedown",u=>{u.preventDefault(),ne="start"}),a.addEventListener("mousedown",u=>{u.preventDefault(),ne="end"}),window.addEventListener("mousemove",u=>l(u.clientX)),window.addEventListener("mouseup",p),o.addEventListener("touchstart",u=>{u.preventDefault(),ne="start"},{passive:!1}),a.addEventListener("touchstart",u=>{u.preventDefault(),ne="end"},{passive:!1}),window.addEventListener("touchmove",u=>l(u.touches[0].clientX),{passive:!0}),window.addEventListener("touchend",p);function _(u){if(!C)return;const m=N-k,f=Math.max(C,Math.min(j-m,k+u));k=f,N=Math.min(j,f+m),$e(),Z&&Z(k,N)}(i=document.getElementById("btn-slice-reset"))==null||i.addEventListener("click",()=>{C&&(k=C,N=j,$e(),Z&&Z(k,N))}),(r=document.getElementById("btn-slice-back"))==null||r.addEventListener("click",()=>_(-3e5)),(c=document.getElementById("btn-slice-forward"))==null||c.addEventListener("click",()=>_(3e5)),(h=document.getElementById("btn-slice-next-window"))==null||h.addEventListener("click",()=>{const u=fs().filter(b=>!b.isClosed).sort((b,v)=>b.createdAt-v.createdAt);if(!u.length||!C)return;const m=u[0].createdAt,f=N-k;k=Math.max(C,Math.min(j-f,m)),N=Math.min(j,k+f),$e(),Z&&Z(k,N)})}function Vs(e){if(document.getElementById("slice-handle-start"))return;const t=`
  position:absolute;top:50%;transform:translate(-50%,-50%);
  width:10px;height:12px;border-radius:2px;
  background:var(--cyan-hi,#22d3ee);border:2px solid #0f172a;
  cursor:ew-resize;z-index:10;user-select:none;touch-action:none;
  display:flex;align-items:flex-end;justify-content:center;
  box-shadow:0 0 0 2px rgba(34,211,238,.4);
 `,s=`
  position:absolute;top:100%;margin-top:3px;left:50%;
  transform:translateX(-50%);white-space:nowrap;
  font-family:monospace;font-size:9px;color:var(--cyan-hi,#22d3ee);
  background:rgba(15,23,42,.85);padding:0px 2px;border-radius:2px;
  pointer-events:none;
 `,n=document.createElement("div");n.id="slice-handle-start",n.style.cssText=t+"background:linear-gradient(180deg,#22d3ee,#0891b2);",n.innerHTML=`<span id="slice-label-start" style="${s}"></span>`;const o=document.createElement("div");o.id="slice-handle-end",o.style.cssText=t+"background:linear-gradient(180deg,#818cf8,#4f46e5);",o.innerHTML=`<span id="slice-label-end" style="${s}"></span>`,e.appendChild(n),e.appendChild(o)}function qs(e){var r;if(!e||!e.nodes||e.nodes.length===0)return'<div class="empty-state">Aguardando evidências para construir o grafo de hipóteses...</div>';const t=e.nodes,s=e.edges||[],n=e.kill_chain_progress||{},a=`
  <div style="margin-bottom: 20px">
   <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 12px">
    🧬 Kill Chain Progress (Global)
   </div>
   <div style="display: flex; flex-wrap: wrap; gap: 8px">
    ${["RECON","INITIAL_ACCESS","EXECUTION","PERSISTENCE","LATERAL_MOVEMENT","EXFILTRATION","IMPACT"].map(c=>{const h=n[c]||0,u=h>.7?"#22c55e":h>.3?"#eab308":"#475569",m=h>=.9;return`
      <div style="flex: 1; min-width: 100px; background: var(--bg3); border-radius: 8px; padding: 8px; text-align: center; border-left: 3px solid ${u}">
       <div style="font-size: 9px; font-family: monospace; color: ${u}; font-weight: 700">${c.replace("_"," ")}</div>
       <div style="font-size: 14px; font-weight: 700; color: ${u}">${Math.round(h*100)}%</div>
       <div style="height: 4px; background: var(--bg2); border-radius: 2px; margin-top: 4px; overflow: hidden">
        <div style="width: ${h*100}%; height: 100%; background: ${u}; border-radius: 2px"></div>
       </div>
       ${m?'<span style="font-size: 8px; color: #22c55e">✓ Completed</span>':""}
      </div>
     `}).join("")}
   </div>
  </div>
 `,l=`
  <div style="margin-bottom: 20px">
   <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 12px">
    🎯 Top Hypotheses (Global Graph)
   </div>
   <div style="display: flex; flex-wrap: wrap; gap: 10px">
    ${t.sort((c,h)=>h.cumulative_score-c.cumulative_score).slice(0,8).map(c=>{const h=c.risk_tier==="CRITICAL"?"#dc2626":c.risk_tier==="HIGH"?"#ea580c":c.risk_tier==="MEDIUM-HIGH"?"#d97706":c.risk_tier==="MEDIUM"?"#ca8a04":"#475569";return`
      <div style="background: var(--bg2); border: 1px solid ${c.confirmed?"#22c55e":"var(--border2)"}; border-radius: 8px; padding: 10px 14px; min-width: 180px; flex: 1">
       <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px">
        <span style="font-size: 12px; font-weight: 700; color: var(--text)">${g(c.label)}</span>
        ${c.confirmed?'<span style="font-size: 10px; background: #22c55e20; color: #22c55e; padding: 2px 6px; border-radius: 4px">✓ Confirmed</span>':""}
       </div>
       <div style="display: flex; justify-content: space-between; align-items: center">
        <span style="font-size: 20px; font-weight: 700; color: ${h}">${Math.round(c.cumulative_score*100)}%</span>
        <span style="font-size: 10px; color: var(--text4)">${c.evidence_count} evidências</span>
       </div>
       <div style="height: 4px; background: var(--bg3); border-radius: 2px; margin-top: 6px; overflow: hidden">
        <div style="width: ${c.cumulative_score*100}%; height: 100%; background: ${h}; border-radius: 2px"></div>
       </div>
       <div style="font-size: 9px; color: var(--text4); margin-top: 4px">Risk: ${c.risk_tier}</div>
      </div>
     `}).join("")}
   </div>
  </div>
 `,p=s.length>0?`
  <div style="margin-bottom: 20px">
   <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 12px">
    🔗 Phase Transitions (Evidence Weight)
   </div>
   <div style="display: flex; flex-wrap: wrap; gap: 6px">
    ${s.slice(0,15).map(c=>`
     <span style="background: var(--bg3); padding: 4px 10px; border-radius: 4px; font-family: monospace; font-size: 10px">
      ${g(c.source)} → ${g(c.target)}
      <span style="color: #22c55e; margin-left: 6px">${Math.round(c.weight*100)}%</span>
      <span style="color: var(--text4); font-size: 8px">(${c.evidence_count}x)</span>
     </span>
    `).join("")}
   </div>
  </div>
 `:"",_=e.total_evidence_windows||0;return`
  <div class="hypothesis-graph-container">
   ${`
  <div style="display: flex; gap: 12px; margin-bottom: 20px; padding: 12px; background: var(--bg3); border-radius: 8px">
   <div>
    <div style="font-size: 10px; color: var(--text4)">Total Nodes</div>
    <div style="font-size: 24px; font-weight: 700; color: var(--cyan-hi)">${t.length}</div>
   </div>
   <div>
    <div style="font-size: 10px; color: var(--text4)">Transitions</div>
    <div style="font-size: 24px; font-weight: 700; color: var(--cyan-hi)">${s.length}</div>
   </div>
   <div>
    <div style="font-size: 10px; color: var(--text4)">Evidence Windows</div>
    <div style="font-size: 24px; font-weight: 700; color: var(--cyan-hi)">${_}</div>
   </div>
   <div>
    <div style="font-size: 10px; color: var(--text4)">Confirmed</div>
    <div style="font-size: 24px; font-weight: 700; color: #22c55e">${((r=e.confirmed_hypotheses)==null?void 0:r.length)||0}</div>
   </div>
  </div>
 `}
   ${a}
   ${l}
   ${p}
   <div style="font-size: 10px; color: var(--text4); padding: 8px; text-align: center; border-top: 1px solid var(--border2); margin-top: 12px">
    🧠 Hypothesis Graph — Memória global fora das janelas. Janelas produzem evidência, o grafo possui a verdade.
   </div>
  </div>
 `}let Ce=(()=>{const e=sessionStorage.getItem("wm_min_score");return e!==null?parseInt(e,10):0})(),ue=(()=>{try{const e=sessionStorage.getItem("wm_risk");return e?new Set(JSON.parse(e)):new Set}catch{return new Set}})();function Ks(){sessionStorage.setItem("wm_risk",JSON.stringify([...ue]))}let Ie="fixed";function ns(e,t){e.dataset.mode=t,e.textContent=t==="adaptive"?"⚡ adaptive":"📐 fixed",e.classList.toggle("wm-mode-adaptive",t==="adaptive")}function Ys(e){Ce=e,sessionStorage.setItem("wm_min_score",String(e))}window.__wmSetMinScore=e=>{Ys(e),window.__wmMinScore=e;const t=document.getElementById("wm-score-display");t&&(t.textContent=String(e)),window.dispatchEvent(new CustomEvent("wm-filter-change",{detail:{minScore:e}}))};window.__wmMinScore=Ce;requestAnimationFrame(async()=>{const e=document.getElementById("wm-score-display");e&&(e.textContent=String(Ce)),ue.forEach(s=>{const n=document.querySelector(`.wm-risk-btn[data-tier="${s}"]`);n&&n.classList.add("active")});try{Ie=(await(await fetch("/api/agent1/window-mode")).json()).mode==="adaptive"?"adaptive":"fixed"}catch{Ie="fixed"}const t=document.querySelector(".wm-mode-btn");t&&ns(t,Ie)});window.__wmToggleMode=async e=>{const t=Ie==="adaptive"?"fixed":"adaptive";Ie=t,ns(e,t);try{await fetch("/api/agent1/window-mode",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode:t})})}catch(s){console.warn("[WindowMode] Failed to set mode:",s)}};window.__wmPushAlertToExtension=e=>{const t=e.dataset;window.postMessage({type:"REDSHIFT_WINDOW_CONTEXT",windowId:t.pushWindowid||"",label:t.pushCategory||"",probability:0,tier:"",cves:[],iocs:[],phases:[],assets:[],siemAlert:{"rule.name":t.pushCategory||"",alert_id:t.pushNumber||"",kill_chain:t.pushKillchain||"",severity:t.pushSeverity||"",timestamp:t.pushTs||"",source:"SOC Dashboard — trigger alert"}},"*")};window.__wmConfirmHypothesis=async(e,t)=>{try{const s=await fetch("/api/agent1/confirm-hypothesis",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({window_id:e,hypothesis_label:t})});if(!s.ok)throw new Error(`HTTP ${s.status}`);const n=await s.json();n.ok===!1&&console.warn("[WindowsPanel] Confirm rejected by server:",n.message),window.dispatchEvent(new CustomEvent("wm-operator-confirmed",{detail:{windowId:e,label:t}}))}catch(s){console.error("[WindowsPanel] Confirm failed:",s)}};let is=sessionStorage.getItem("wm_sort")||"score";function Qs(e){is=e,sessionStorage.setItem("wm_sort",e)}const Gt={CRITICAL:0,HIGH:1,"MEDIUM-HIGH":2,MEDIUM:3,"LOW-MED":4,LOW:5,"—":6};function qe(e){var t,s;return((s=(t=e.current_ciso_options)==null?void 0:t[0])==null?void 0:s.risk_tier)||"—"}window.__wmToggleRisk=(e,t)=>{ue.has(e)?(ue.delete(e),t.classList.remove("active")):(ue.add(e),t.classList.add("active")),Ks(),window.dispatchEvent(new CustomEvent("wm-filter-change"))};window.__wmSetSort=e=>{Qs(e),document.querySelectorAll(".wm-sort-btn").forEach(t=>{t.classList.toggle("active",t.dataset.sort===e)}),window.dispatchEvent(new CustomEvent("wm-filter-change"))};function Zs(e){return is==="time"?[...e].sort((t,s)=>s.created_at_ms-t.created_at_ms):[...e].sort((t,s)=>{const n=Gt[qe(t)]??6,o=Gt[qe(s)]??6;return n!==o?n-o:(s.phase_score||0)-(t.phase_score||0)})}function en(e,t=Date.now()){if(!e||e.length===0)return'<div class="empty-state">Nenhuma janela activa. Aguardando triggers...</div>';const s=e.filter(i=>{var c;return i.is_closed?!1:(i.alert_count||((c=i.alerts)==null?void 0:c.length)||0)>0}),n=e.filter(i=>i.is_closed),o=s.filter(i=>(i.phase_score||0)>=Ce),a=ue.size===0?o:o.filter(i=>ue.has(qe(i))),d=Zs(a),l=s.length-d.length,p=d.length>0?d.map(i=>Ft(i,!0,t)).join(""):`<div class="empty-state" style="grid-column:1/-1;font-size:11px;padding:10px">
    ${s.length>0?`${l} janela${l!==1?"s":""} oculta${l!==1?"s":""} — score &lt; ${Ce}`:"Nenhuma janela activa."}
   </div>`,_=n.length>0?`
  <div class="wm-section-label closed" style="grid-column:1/-1">📋 FECHADAS (${n.length})</div>
  ${n.slice(0,15).map(i=>Ft(i,!1,t)).join("")}
 `:"";return`${p}${_}`}function be(e){if(e.ts){const s=new Date(e.ts).getTime();if(s>0)return s}const t=e.timestamp_ms;return t!=null&&t>0?t:0}function tn(e,t,s,n){if(!e.length)return'<div class="wm-no-alerts">⏳ Nenhum alerta nesta janela ainda</div>';const o=s-t||1,a=[...e].sort((i,r)=>be(i)-be(r)),d=`tl${Math.random().toString(36).slice(2,8)}`,l=a.map((i,r)=>{var y;const c=be(i),h=c>0?Math.max(2,Math.min(97,(c-t)/o*100)):Math.max(2,Math.min(97,r/Math.max(1,a.length-1)*97)),u=i.kill_chain||((y=i.phases_detected)==null?void 0:y[0])||n[r]||"",m=i.is_noise||!1,f=r===0,b=m?"#64748b":Pe[u]||"#94a3b8",v=m?"NS":He[u]||u.slice(0,2)||"AL",M=c>0?new Date(c).toLocaleTimeString("pt-PT").slice(0,5):"—",T=i.severity==="critical"?"#dc2626":i.severity==="high"?"#ea580c":i.severity==="medium"?"#d97706":"#22c55e",G=f?"15px":m?"8px":"13px",L=f?`3px solid ${T}`:`1.5px solid ${T}`,z=f?`box-shadow:0 0 0 3px rgba(34,211,238,.35),0 0 8px ${b};`:`box-shadow:0 0 4px ${b};`;return`
   <div class="wm-pin ${d}"
    style="position:absolute;left:${h}%;top:50%;transform:translate(-50%,-50%);
       width:${G};height:${G};border-radius:50%;background:${b};
       border:${L};cursor:pointer;z-index:${f?15:10};
       transition:transform .15s;${z}${m?"opacity:.6;":""}"
    title="${g("#"+(i.number||"?")+" · "+(i.title||i.category||v)+" · "+M)}"
    ${f?`data-push-category="${g(i.category||"")}"
      data-push-number="${g(i.number||"")}"
      data-push-severity="${g(i.severity||"")}"
      data-push-killchain="${g(i.kill_chain||"")}"
      data-push-ts="${g(i.ts||"")}"
      data-push-windowid="${g(i.window_id||"")}"
      onclick="window.__wmPushAlertToExtension(this)"`:""}>
    <div style="position:absolute;top:calc(100% + 4px);left:50%;transform:translateX(-50%);
      color:${b};font-size:8px;font-weight:700;
      white-space:nowrap;font-family:monospace;
      display:block;pointer-events:none;z-index:20;text-align:center;">
 ${f?"▶ ":""}${v}
</div>
   </div>`}).join(""),p=new Date(be(a[0])).toLocaleTimeString("pt-PT").slice(0,5),_=a.length>1?new Date(be(a[a.length-1])).toLocaleTimeString("pt-PT").slice(0,5):"";return`
  <style>
   .${d}:hover{transform:translate(-50%,-50%) scale(1.35)!important;z-index:30;}
   .${d}:hover>div{display:block!important;}
  </style>
  <div style="position:relative;height:32px;margin:4px 0 2px">
   <div style="position:absolute;top:50%;left:0;right:0;height:2px;
         background:linear-gradient(90deg,var(--cyan),#475569);
         transform:translateY(-50%);border-radius:2px"></div>
   ${l}
   <div style="position:relative;height:14px">
    <div style="position:absolute;left:0;bottom:4px;font-size:8px;font-family:monospace;color:var(--text4)">${p}</div>
    ${_?`<div style="position:absolute;right:0;bottom:-2px;font-size:8px;font-family:monospace;color:var(--text4)">${_}</div>`:""}
   </div>
  </div>`}function sn(e){const t=e.confirmed_by||"",s=e.confirmed_label||"",n=e.close_reason||"",o=!!s;return t==="operator"||n.startsWith("✋")?'<div class="wm-closed operator">✋ Confirmado pelo analista</div>':t==="finish"||n.startsWith("⏹")?'<div class="wm-closed" style="opacity:.6">⏹ Finalizado</div>':o?`<div class="wm-closed auto">⚡ ${g(s)} — relatório gerado</div>`:t==="timeout"||n==="timeout"?'<div class="wm-closed timeout" style="opacity:.6">⏱ Timeout — sem relatório</div>':t==="done"?'<div class="wm-closed" style="opacity:.6">⏹ Dataset concluído</div>':'<div class="wm-closed" style="opacity:.6">✓ Fechada</div>'}function Ft(e,t,s=Date.now()){var le,de;const n=e.alerts||[],o=e.phases||[],a=e.current_ciso_options||[],d=e.phase_score||0,l=a[0],p=l?Math.round(l.probability*100):0,_=p>80?"#dc2626":p>60?"#ea580c":"#d97706",i=new Date(e.created_at_ms).toLocaleTimeString("pt-PT").slice(0,5),r=new Date(e.expires_at_ms).toLocaleTimeString("pt-PT").slice(0,5);if(!t){const x=e.confirmed_label||((de=(le=e.current_ciso_options)==null?void 0:le[0])==null?void 0:de.category)||"",A=x?Be(x):g(e.window_id.slice(0,8)),D=e.confirmed_probability,R=D!=null&&D>0?`${Math.round(D*100)}%`:p>0?`${p}%`:"",W=(e.alerts||[]).map(P=>P.number).filter(P=>P&&P!=="—").join(", ");return`
  <div class="wm-card closed" data-window-id="${g(e.window_id)}">
    <div class="wm-line1">
      <span class="wm-timerange">${i} → ${r}</span>
      <span class="wm-pill wm-badge-impact" style="color:${_};border-color:${_}33">
        ${A} ${R}
      </span>
      <span class="wm-pill" style="margin-left:auto">Score: ${d}</span>
    </div>
    ${W?`
    <div style="padding:2px 6px 4px;font-family:var(--mono);font-size:9px;color:var(--text4)">
      📋 ${g(W)}
    </div>`:""}
    ${sn(e)}
  </div>`}const c=Math.max(0,e.expires_at_ms-s),h=Math.floor(c/6e4),u=Math.floor(c%6e4/1e3),m=`${h}:${u.toString().padStart(2,"0")}`,f=c<6e4,b=85,v=75,M=t&&p>=b&&c>0,T=t&&p>=b&&c===0,G=t&&p>=v,L=p>=85?"#dc2626":p>=70?"#ea580c":p>=50?"#d97706":"#64748b",z=x=>x?new Date(x).toLocaleTimeString("pt-PT").slice(0,5):"—",y=x=>x.replace("MEDIUM-HIGH","MH").replace("MEDIUM","ME").replace("CRITICAL","CR").replace("HIGH","HI").replace("LOW-MED","LM").replace("LOW","LO"),$=x=>x==="CRITICAL"?"#dc2626":x==="HIGH"?"#ea580c":x.includes("MEDIUM")?"#d97706":"#64748b",O=e.window_mode==="adaptive"?'<span class="wm-mode adaptive">⚡</span>':"",B=M?`<span class="wm-timer-inline${f?" critical":""}" data-expires="${e.expires_at_ms}" data-confirm-pct="${p}">⏱ ${m}</span>`:T?`<span class="wm-timer-inline expired" data-expires="${e.expires_at_ms}">⏳ A confirmar...</span>`:"",q=o.length>0?`<span style="font-size:10px">🎯 ${o.length} Fase${o.length!==1?"s":""}: ${o.map((x,A)=>`<span style="color:${Pe[x]||"#64748b"}">${He[x]||x.slice(0,2)}</span>${A<o.length-1?"→":""}`).join("")}</span>`:"",se=x=>{const A=x.toLowerCase().split(/\s+/).filter(P=>P.length>4),D=[...n].reverse().find(P=>A.some(X=>(P.category||"").toLowerCase().includes(X)||(P.kill_chain||"").toLowerCase().includes(X)))||n[0]||null,R=(D==null?void 0:D.number)||"";return{num:R&&!R.startsWith("W")&&R.length<20?R:"",alert:D||null}},F=a.length>0?`
  <div class="wm-hyps">
   ${a.slice(0,3).map((x,A)=>{const D=Math.round(x.probability*100),R=x.risk_tier||"—",W=$(R),P=y(R),{num:X,alert:K}=se(x.category),Y=A===0,Fe=X&&K?`
     <span class="wm-hyp-ev clickable"
      title="Carregar alerta #${g(X)} na extensão para análise SIEM"
      data-push-category="${g(K.category||"")}"
      data-push-number="${g(X)}"
      data-push-severity="${g(K.severity||"")}"
      data-push-killchain="${g(K.kill_chain||"")}"
      data-push-ts="${g(K.ts||"")}"
      data-push-windowid="${g(K.window_id||e.window_id)}"
      onclick="window.__wmPushAlertToExtension(this)">
      🔍 #${g(X)}
     </span>`:"";return`<div class="wm-hyp-row${Y?" top":""}">
     <div class="wm-hyp-info">
      <span class="wm-hyp-name${Y?" top":""}" style="color:${Y?W:"var(--text4)"}">${g(x.category)}</span>
      ${Fe}
     </div>
     ${G?`<button class="wm-hyp-btn${Y?" top":""}"
            style="background:${W}${Y?"22":"11"};border-color:${W}${Y?"55":"28"};color:${W}"
            data-confirm-btn="${g(e.window_id)}"
            onclick="window.__wmConfirmHypothesis('${g(e.window_id)}','${g(x.category)}')"
            title="${g(x.category)} — ${R}">
            ${Be(x.category)} ${P} ${D}%
        </button>`:`<span class="wm-hyp-pct-badge" style="color:${W}">${D}%</span>`}
    </div>`}).join("")}
  </div>`:'<div class="wm-analyzing">🔍 A analisar...</div>',U=(()=>{const x=n.map(A=>A.number).filter(A=>A&&A!=="—");return x.length>0?x.join(", "):""})(),ce=U?`<span style="font-family:var(--mono);font-size:9px;color:var(--cyan-hi)">📋 ${g(U)}</span>`:"";return`
  <div class="wm-card active" data-window-id="${g(e.window_id)}">
   <div class="wm-line1">
    <span style="font-family:var(--mono);font-size:9px;color:var(--text4)">ID: ${g(e.window_id)}</span>
    <span class="wm-timerange" style="color:${L}">🕐 ${z(e.created_at_ms)} → ${z(e.expires_at_ms)}</span>
    <span class="wm-pill">${n.length} alerta${n.length!==1?"s":""}</span>
    <span class="wm-pill">Score: ${d}</span>
   </div>
   <div class="wm-line1">
    ${ce}
   </div>
   <div class="wm-line1">
    ${q}
   </div>
   ${tn(n,e.created_at_ms,e.expires_at_ms,o)}
   <div class="wm-line1">
    <span style="margin-left:auto;display:flex;align-items:center;gap:4px">${B}${O}</span>
   </div>
   ${F}
  </div>`}var Ne=(e=>(e[e.NONE=0]="NONE",e[e.ERROR=1]="ERROR",e[e.WARN=2]="WARN",e[e.INFO=3]="INFO",e[e.DEBUG=4]="DEBUG",e[e.TRACE=5]="TRACE",e))(Ne||{});const nn={ERROR:1,WARN:2,INFO:3,DEBUG:4,TRACE:5};function on(e){return nn[e]??3}class an{constructor(){fe(this,"consoleLevel",3);fe(this,"storageLevel",4);fe(this,"maxStorageEntries",1e4);fe(this,"storageKey","dashboard_debug_logs");fe(this,"logs",[]);this.loadFromStorage(),this.setupKeyboardShortcut()}setupKeyboardShortcut(){window.addEventListener("keydown",t=>{t.ctrlKey&&t.shiftKey&&t.key==="L"&&(t.preventDefault(),this.downloadLogs(),console.log("[Logger] Logs downloaded via keyboard shortcut")),t.ctrlKey&&t.shiftKey&&t.key==="C"&&(t.preventDefault(),this.clearLogs(),console.log("[Logger] Logs cleared via keyboard shortcut"))})}loadFromStorage(){try{const t=localStorage.getItem(this.storageKey);t&&(this.logs=JSON.parse(t),this.logs.length>this.maxStorageEntries&&(this.logs=this.logs.slice(-this.maxStorageEntries)),console.log(`[Logger] Loaded ${this.logs.length} logs from storage`))}catch{console.warn("[Logger] Failed to load logs from storage")}}saveToStorage(){try{this.logs.length>this.maxStorageEntries&&(this.logs=this.logs.slice(-this.maxStorageEntries)),localStorage.setItem(this.storageKey,JSON.stringify(this.logs))}catch{console.warn("[Logger] Failed to save logs to storage")}}shouldLogToConsole(t){return t<=this.consoleLevel&&t>=3}shouldLogToStorage(t){return t<=this.storageLevel}sanitizeData(t){if(!t)return t;try{const s=new WeakSet;return JSON.parse(JSON.stringify(t,(n,o)=>{if(typeof o=="object"&&o!==null){if(s.has(o))return"[Circular]";s.add(o)}return typeof o=="string"&&o.length>500?o.substring(0,500)+"...":Array.isArray(o)&&o.length>100?o.slice(0,100).map(a=>typeof a=="object"&&a!==null?{...a,_truncated:!0}:a).concat({_truncated:!0,_original_length:o.length}):o}))}catch{return"[Unserializable]"}}log(t,s,n,o,a){const d={timestamp:new Date().toISOString(),level:s,module:n,message:o,data:a?this.sanitizeData(a):void 0};if(this.shouldLogToConsole(t)){const l=`[${n}] ${o}`;t===1?console.error(l,a||""):t===2?console.warn(l,a||""):console.log(l,a?"(see storage for details)":"")}this.shouldLogToStorage(t)&&(this.logs.push(d),this.logs.length>this.maxStorageEntries&&(this.logs=this.logs.slice(-this.maxStorageEntries)),this.saveToStorage())}error(t,s,n){this.log(1,"ERROR",t,s,n)}warn(t,s,n){this.log(2,"WARN",t,s,n)}info(t,s,n){this.log(3,"INFO",t,s,n)}debug(t,s,n){this.log(4,"DEBUG",t,s,n)}trace(t,s,n){this.log(5,"TRACE",t,s,n)}getLogs(t=4){return this.logs.filter(s=>on(s.level)<=t)}getLogsByModule(t,s=4){return this.getLogs(s).filter(n=>n.module===t)}getLogsByLevel(t){const s=Ne[t];return this.logs.filter(n=>n.level===s)}clearLogs(){this.logs=[],localStorage.removeItem(this.storageKey),this.info("Logger","Logs cleared")}downloadLogs(){const t=new Blob([JSON.stringify(this.logs,null,2)],{type:"application/json"}),s=URL.createObjectURL(t),n=document.createElement("a");n.href=s,n.download=`dashboard_logs_${new Date().toISOString().replace(/[:.]/g,"-")}.json`,n.click(),URL.revokeObjectURL(s),this.info("Logger",`Logs downloaded (${this.logs.length} entries)`)}setConsoleLevel(t){this.consoleLevel=t;const s=Ne[t];this.info("Logger",`Console level set to ${s}`)}setStorageLevel(t){this.storageLevel=t;const s=Ne[t];this.info("Logger",`Storage level set to ${s}`)}getStats(){const t={ERROR:0,WARN:0,INFO:0,DEBUG:0,TRACE:0},s={};for(const n of this.logs)t[n.level]=(t[n.level]||0)+1,s[n.module]=(s[n.module]||0)+1;return{total:this.logs.length,byLevel:t,byModule:s}}}const ae=new an;function rn(e,t,s){var o;let n=null;s&&(n={type:t,...s.window_id&&{window_id:s.window_id},...s.alert_count&&{alert_count:s.alert_count},...s.reason&&{reason:s.reason}},t==="next_alert_info"&&(n.current_index=s.current_alert_index,n.next_index=s.next_alert_index,n.gap_ms=s.gap_ms,n.is_last=s.is_last),t==="dataset_bounds"&&(n.total_alerts=s.total_alerts,n.speed_factor=s.speed_factor,n.first_alert=(o=s.first_alert)==null?void 0:o.number)),ae.debug(e,`SSE:${t}`,n)}function Ut(e,t,s,n){ae.debug(e,`Window ${t}`,{windowId:s,...n})}function cn(e,t,s,n){const o=(s*100).toFixed(1);ae.info(e,`✓ CONFIRMED: ${t} (${o}%)`)}function ln(e,t,s){ae.error(e,t,s)}function J(e){return(e||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")}function dn(e){const t=new Date(e),s=t.getHours().toString().padStart(2,"0"),n=t.getMinutes().toString().padStart(2,"0"),o=t.getSeconds().toString().padStart(2,"0");return`${s}:${n}:${o}`}function Xt(e){return e.is_noise?"#475569":e.phase&&Pe[e.phase]?Pe[e.phase]:e.severity==="critical"?"#dc2626":e.severity==="high"?"#ea580c":e.severity==="medium"?"#d97706":"#38bdf8"}function pn(e){return e==="critical"?"#dc2626":e==="high"?"#ea580c":e==="medium"?"#d97706":"rgba(255,255,255,.6)"}function mn(e){return e.is_noise?"NS":e.phase&&He[e.phase]?He[e.phase]:(e.category||e.type||"").slice(0,2).toUpperCase()||"AL"}function un(e){return 20+(e-1)*72+48}function gn(e){const{alerts:t,height:s=140,onAlertClick:n,selectedAlertNumber:o}=e;if(!t||t.length===0)return`<div class="timeline-empty-state">
 <div class="empty-icon">📡</div>
 <div>Aguardando alertas...</div>
 </div>`;const a=[...t].sort((y,$)=>y.timestamp_ms-$.timestamp_ms),d=a.length,l=72,p=20,_=48,i=32,r=s-18,c=s-4,h=16,u=i+14,m=un(d),f=a.map((y,$)=>$===0?0:y.timestamp_ms-a[$-1].timestamp_ms),b=Math.max(1,...f);let v="";for(let y=1;y<d;y++){const $=p+(y-1)*l,O=p+y*l,B=($+O)/2,q=Math.max(3,f[y]/b*h),se=f[y]>b*.7?"#f97316":f[y]>b*.4?"#fbbf24":"#38bdf822";v+=`<rect x="${$+4}" y="${u}" width="${l-8}" height="${q}"
 fill="${se}" fill-opacity="0.25" rx="2"/>`;const F=Math.round(f[y]/1e3);F>0&&(v+=`<text x="${B}" y="${u+q+9}"
  text-anchor="middle" font-family="'IBM Plex Mono',monospace"
  font-size="7" fill="#64748b">+${F}s</text>`)}const M=`<line x1="${p}" y1="${r}"
 x2="${m-_+20}" y2="${r}"
 stroke="rgba(148,163,184,.3)" stroke-width="1"/>`;let T="";for(let y=0;y<d-1;y++){const $=p+y*l,O=p+(y+1)*l,B=Xt(a[y]);T+=`<line x1="${$}" y1="${i}" x2="${O}" y2="${i}"
 stroke="${B}" stroke-width="1.5" stroke-opacity=".5"/>`}let G="";for(let y=0;y<d;y++){const $=a[y],O=p+y*l,B=Xt($),q=pn($.severity),se=mn($),F=o===$.number,U=F?15:11,ce=dn($.timestamp_ms),le=n?`onclick="window._onTimelineAlertClick&&window._onTimelineAlertClick('${J($.number)}')" style="cursor:pointer"`:"",de=F?`<circle cx="${O}" cy="${i}" r="${U+5}" fill="${B}" fill-opacity=".15"/>`:"",A=$.is_noise===!0?'opacity="0.4"':"";G+=`
 <g class="tl-pin" data-n="${J($.number)}" ${le} ${A}>
  ${de}
  <circle cx="${O}" cy="${i}" r="${U+3}" fill="${B}" fill-opacity=".12"/>
  <circle cx="${O}" cy="${i}" r="${U}"
  fill="${B}" stroke="${q}" stroke-width="2"/>
  <text x="${O}" y="${i+4}" text-anchor="middle"
  font-family="'IBM Plex Mono',monospace" font-size="8" font-weight="700"
  fill="#0f172a" style="pointer-events:none">${J(se)}</text>
  <text x="${O}" y="${i-U-5}" text-anchor="middle"
  font-family="'IBM Plex Mono',monospace" font-size="8" fill="${B}"
  style="pointer-events:none">${J($.number)}</text>
  <text x="${O}" y="${c}" text-anchor="middle"
  font-family="'IBM Plex Mono',monospace" font-size="8" fill="rgba(148,163,184,.8)"
  style="pointer-events:none">${J(ce)}</text>
  <title>${J($.number)} | ${J($.category)}/${J($.type)} | ${J(ce)} | ${J($.phase||"—")}</title>
 </g>`}const L=p+(d-1)*l+24,z=`
 <line x1="${L}" y1="${i-18}" x2="${L}" y2="${r}"
 stroke="#22c55e" stroke-width="1.5" stroke-dasharray="4,3"/>
 <text x="${L+4}" y="${i-8}" font-family="'IBM Plex Mono',monospace"
 font-size="8" font-weight="700" fill="#22c55e">NOW</text>`;return`<div class="timeline-scroll-inner" style="display: inline-block; min-width: 100%;">
 <svg width="${m}" height="${s}"
 style="display:block;background:var(--bg2);border-radius:6px;">
 ${v}
 ${T}
 ${M}
 ${G}
 ${z}
 </svg>
</div>`}function fn(e){window._onTimelineAlertClick=e}let H=null,Ae=null,Oe=!0;function hn(e="timeline-content"){if(H=document.getElementById(e),!H){console.warn("Scroll container not found:",e);return}H.style.overflowX="scroll",H.style.overflowY="hidden",Ae&&Ae.disconnect(),Ae=new ResizeObserver(()=>{Oe&&Ee(),De()}),Ae.observe(H),new MutationObserver(()=>{Oe&&Ee()}).observe(H,{childList:!0,subtree:!0,attributes:!0,attributeFilter:["style","class"]}),setTimeout(()=>{Ee(),De()},100),window.addEventListener("resize",()=>{setTimeout(()=>{Oe&&Ee(),De()},50)})}function De(){if(!H)return;H.scrollWidth>H.clientWidth?H.style.overflowX="scroll":H.style.overflowX="auto"}function Ee(){H&&(Oe=!0,H.scrollLeft=H.scrollWidth,De())}const oe="Dashboard";let ie=null,re=new Map,ee=null,w=[],_e=new Set,Te=new Set,me=0,Re=0,os=new Map,We=new Map;Ss(()=>S());function he(e,t){const s=document.getElementById(e);s&&s.innerHTML!==t&&(s.innerHTML=t)}let ge=new Set;const Me=new Map;function je(){const e=document.getElementById("reports-pending-badge"),t=document.getElementById("reports-pending-count"),s=ge.size;e&&(e.style.display=s>0?"":"none",e.title=s>0?`Em geração:
${[...ge].join(`
`)}`:""),t&&(t.textContent=String(s))}function _n(){const e=Kt();os=new Map(e.map(a=>[String(a.number),a]));const t=document.getElementById("timeline-content"),s=document.getElementById("timeline-alert-count");if(!t)return;if(!e.length){t.innerHTML=`<div class="timeline-strip-scroll" id="timeline-scroll-container" style="overflow-x: scroll !important;">
 <div class="timeline-empty-state">
  <div class="empty-icon">📡</div>
  <div>Aguardando alertas...</div>
 </div>
 </div>`,s&&(s.textContent="0");return}const n=e.map(a=>{var d;return{number:a.number,timestamp_ms:new Date(a.ts).getTime(),category:a.category,type:a.category||a.title||"",phase:a.kill_chain||((d=a.phases_detected)==null?void 0:d[0]),severity:a.severity,window_id:a.window_id,is_noise:a.is_noise===!0}}),o=w.length>0?Me.get(w[0].window_id):void 0;t.innerHTML=`
 <div class="timeline-strip-scroll" id="timeline-scroll-container" style="overflow-x: scroll !important; width: 100%;">
  ${gn({alerts:n,height:72,selectedAlertNumber:o,onAlertClick:a=>{}})}
 </div>
`,s&&(s.textContent=`${e.length}`),hn("timeline-scroll-container"),setTimeout(()=>{Ee();const a=document.getElementById("timeline-scroll-container");a&&(a.style.overflowX="scroll")},50)}function S(){var o,a;const e=Qe(),t=Yt();_n(),he("hypothesis-graph",qs(ee)),he("windows-panel",en(w,me||Date.now())),w.filter(d=>!d.is_closed).forEach(as),he("agent2-panel",Hs([],0,e)),he("footer-chips",`<span class="fchip">Alerts <span class="val">${t}</span></span><span class="fchip">Windows <span class="val">${w.filter(d=>!d.is_closed).length}</span></span><span class="fchip">Nodes <span class="val">${((o=ee==null?void 0:ee.nodes)==null?void 0:o.length)||0}</span></span><span class="fchip">Confirmed <span class="val" style="color:#22c55e">${((a=ee==null?void 0:ee.confirmed_hypotheses)==null?void 0:a.length)||0}</span></span>`);const s=document.getElementById("active-windows-badge");s&&(s.textContent=`${w.filter(d=>!d.is_closed).length} ativas`);const n=document.getElementById("reports-count-badge");n&&(n.textContent=`${e.length}`),he("footer-conn",Ws(hs()))}function wn(e,t){re.has(e)&&clearTimeout(re.get(e));const s=t-Date.now();s>0&&s<60*60*1e3&&re.set(e,setTimeout(()=>{Zt(e,"timeout"),S()},s))}function Ke(e){const t=document.getElementById("btn-window-mode");if(!t)return;const s=e==="adaptive";t.textContent=s?"⚡ adaptive":"📐 fixed",t.classList.toggle("wm-mode-adaptive",s)}function Jt(e){const t=document.getElementById("windows-panel");t&&t.style.setProperty("--wm-cols",String(e)),document.querySelectorAll(".grid-btn").forEach(s=>{s.classList.toggle("active",parseInt(s.dataset.cols||"0",10)===e)})}function vn(){var n,o,a,d;(n=document.getElementById("btn-clear-session"))==null||n.addEventListener("click",()=>{confirm("Clear session data and reset?")&&(Object.values(V).forEach(l=>sessionStorage.removeItem(l)),Te.clear(),_e.clear(),location.reload())}),fetch("/api/config").then(l=>l.ok?l.json():null).then(l=>{l!=null&&l.window_mode&&Ke(l.window_mode)}).catch(()=>{});const e=document.getElementById("graph-overlay"),t=document.getElementById("graph-overlay-backdrop");(o=document.getElementById("btn-graph-toggle"))==null||o.addEventListener("click",()=>{e.style.display=e.style.display==="none"?"flex":"none"}),(a=document.getElementById("btn-graph-close"))==null||a.addEventListener("click",()=>{e.style.display="none"}),t==null||t.addEventListener("click",()=>{e.style.display="none"}),document.addEventListener("keydown",l=>{l.key==="Escape"&&(e.style.display="none")}),(d=document.getElementById("btn-finish"))==null||d.addEventListener("click",async()=>{const l=document.getElementById("btn-finish"),p=w.filter(_=>!_.is_closed);if(p.length===0){alert("Não há janelas activas para finalizar.");return}if(confirm(`Forçar conclusão de ${p.length} janela${p.length!==1?"s":""} activa${p.length!==1?"s":""}?

Todas as janelas serão fechadas e um log de classificações CISO gerado para comparação académica com o dataset.`)){l.disabled=!0,l.textContent="⏳ A processar...";try{const _=await fetch("/api/agent1/finish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({windows:p.map(r=>{var c,h,u,m,f,b;return{window_id:r.window_id,top_hypothesis:((h=(c=r.current_ciso_options)==null?void 0:c[0])==null?void 0:h.category)||"",probability:((m=(u=r.current_ciso_options)==null?void 0:u[0])==null?void 0:m.probability)||0,risk_tier:((b=(f=r.current_ciso_options)==null?void 0:f[0])==null?void 0:b.risk_tier)||"—",all_hypotheses:(r.current_ciso_options||[]).map(v=>({category:v.category,probability:v.probability,risk_tier:v.risk_tier})),phases:r.phases||[],phase_score:r.phase_score||0,alert_count:r.alert_count||0,created_at_ms:r.created_at_ms,expires_at_ms:r.expires_at_ms,alerts:(r.alerts||[]).map(v=>({number:v.number||v.Number||"",category:v.category||v.Category||"",phase:v.kill_chain||v.phase||v.Phase||"",severity:v.severity||v.Severity||"",ts:v.ts||""}))}})})});if(!_.ok)throw new Error(`HTTP ${_.status}`);const i=await _.json();p.forEach(r=>{const c=w.findIndex(h=>h.window_id===r.window_id);c>=0&&(w[c]={...w[c],is_closed:!0,close_reason:"⏹ Finalizado",confirmed_by:"finish"})}),S(),l.textContent="✓ Concluído",l.style.color="#22c55e",i.log_file&&setTimeout(()=>alert(`✓ Log gerado: ${i.log_file}

${i.summary||""}

Verifica a pasta reports/ do projecto.`),300)}catch(_){l.textContent="⏹ Finish",l.disabled=!1,alert(`Erro: ${_}`)}}});const s=parseInt(sessionStorage.getItem("wm_cols")||"4",10);Jt(s),document.querySelectorAll(".grid-btn").forEach(l=>{l.addEventListener("click",()=>{const p=parseInt(l.dataset.cols||"2",10);Jt(p),sessionStorage.setItem("wm_cols",String(p))})})}function Xe(e,t){return{number:e.number||e.Number||e.alert_id||String(e.index||""),title:e.title||`${e.category||e.Category||""} / ${e.type||e.Type||""}`,severity:e.severity||e.Severity||"medium",category:e.category||e.Category||"",ts:e.ts||(e.timestamp_iso&&e.timestamp_iso!==""?e.timestamp_iso:null)||(e.timestamp_ms!=null&&e.timestamp_ms>0?new Date(e.timestamp_ms).toISOString():e._timestamp_ms!=null&&e._timestamp_ms>0?new Date(e._timestamp_ms).toISOString():new Date(e.TimestampMs||0).toISOString()||new Date().toISOString()),source:e.source||e.Source||"Agent1",affected_asset:e.affected_asset||e.AffectedAsset||"",mitre:e.mitre||e.Mitre||"",kill_chain:e.phase||e.Phase||"",phases_detected:e.phases_detected||(e.phase||e.Phase?[e.phase||e.Phase]:[]),classifications:[],primary_ciso:{ciso_category_id:0,ciso_category_name:"",risk_tier:"—",plausibility:0},soc_routing:"",tlp:"green",tags:"",emitted_at:new Date().toISOString(),detected_threat_type:"",ciso_state:"",phase_score:0,trigger_type:"alert",discard_reason:"",is_discarded:!1,window_id:t,timestamp_ms:e.timestamp_ms||e._timestamp_ms||0,is_noise:e.is_noise===!0}}const ke=new Set,yn=75;function as(e){var l,p,_;if(ke.has(e.window_id))return;const t=e.current_ciso_options||[];if((t[0]?Math.round(t[0].probability*100):0)<yn)return;const n=e.alerts||[],o=/CVE-\d{4}-\d{4,}/gi,a=[],d=new Set;n.forEach(i=>{const r=JSON.stringify(i);let c;for(o.lastIndex=0;(c=o.exec(r))!==null;){const h=c[0].toUpperCase();d.has(h)||(d.add(h),a.push(h))}}),ke.add(e.window_id),window.postMessage({type:"REDSHIFT_WINDOW_CONTEXT",windowId:e.window_id,label:((l=t[0])==null?void 0:l.category)||"",probability:((p=t[0])==null?void 0:p.probability)||0,tier:((_=t[0])==null?void 0:_.risk_tier)||"",cves:a,iocs:[],phases:e.phases||[],assets:[],...(()=>{var u,m,f,b;const i=Me.get(e.window_id),r=i?We.get(i):null;console.log("[EXT] window_id:",e.window_id,"triggerNum:",i,"rawTrigger:",r,"rawKeys:",[...We.keys()].slice(0,5));const c=new Set(["AGENT1_","AGENT1","AGENT2"]);return{siemAlert:(v=>Object.fromEntries(Object.entries(v).filter(([,M])=>M!==""&&M!=null)))(r?{alert_number:r.Number||"",title:r.Title||"",description:r.Description||"",mitre_attack:r.MitreAttack||"",affected_asset:r.AffectedAsset||"",tags:r.Tags||"",tlp:r.TLP||"",priority:r.Priority||"",severity:r.Severity||"",source:c.has(r.Source||"")?"":r.Source||"",kill_chain:(e.phases||[]).join(" → "),alert_count:n.length,cves_detected:a,window_id:e.window_id,phase_score:e.phase_score||0,hypothesis:((u=t[0])==null?void 0:u.category)||"",risk_tier:((m=t[0])==null?void 0:m.risk_tier)||""}:{hypothesis:((f=t[0])==null?void 0:f.category)||"",risk_tier:((b=t[0])==null?void 0:b.risk_tier)||"",kill_chain:(e.phases||[]).join(" → "),alert_count:n.length,cves_detected:a,window_id:e.window_id,phase_score:e.phase_score||0})}})()},"*")}async function ze(e,t=0){if(!(Te.has(e)||_e.has(e))){Te.add(e),_e.add(e);try{const s=await fetch("/api/agent1/process-next",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({alert_index:e})});_e.delete(e),(s.status===400||s.status===503)&&t<10&&setTimeout(()=>{Te.delete(e),ze(e,t+1)},1e3)}catch{_e.delete(e),t<5&&setTimeout(()=>ze(e,t+1),1e3)}}}function rs(){ie=new EventSource("/events"),ie.onopen=()=>{Ht("connected"),S()},ie.onmessage=e=>{var t,s,n,o,a,d,l,p;try{const{type:_,payload:i}=JSON.parse(e.data);switch(rn(oe,_,i),_){case"alert":{const r=String(i.number||i.Number||"");r&&We.set(r,i),w.filter(m=>!m.is_closed&&ke.has(m.window_id)).forEach(m=>{Me.get(m.window_id)===r&&(ke.delete(m.window_id),as(m))});const c=Xe(i,i.window_id);c.is_noise=i.is_noise===!0;const h=i.timestamp_ms||new Date(i.ts||"").getTime();h&&h>me&&(me=h),Kt().some(m=>m.number===c.number)||(bs(c),vs(Yt()+1));const u=w.findIndex(m=>m.window_id===i.window_id);if(u>=0){const m=w[u].alerts||[];m.some(f=>f.number===c.number)||m.push(c),w[u]={...w[u],alert_count:m.length,alerts:m}}S();break}case"window_created":{Ut(oe,"created",i.window_id,{});const r=String(i.trigger_alert_number||((t=i.trigger_alert)==null?void 0:t.number)||((s=i.trigger_alert)==null?void 0:s.Number)||"");r&&Me.set(i.window_id,r);const c=i.trigger_alert?Xe(i.trigger_alert,i.window_id):null,h=c?[c]:[];xs({windowId:i.window_id,hypothesisLabel:i.hypothesis_label||"Analyzing...",probability:i.probability||0,phaseScore:i.phase_score||0,phases:i.phases||[],createdAt:i.created_at_ms,expiresAt:i.expires_at_ms,alerts:h,isClosed:!1,isConfirmed:!1}),wn(i.window_id,i.expires_at_ms),w=[{window_id:i.window_id,created_at_ms:i.created_at_ms,expires_at_ms:i.expires_at_ms,alert_count:h.length,phases:i.phases||[],phase_score:i.phase_score||0,is_closed:!1,current_ciso_options:i.ciso_options||[],alerts:h,window_mode:i.window_mode||"fixed"},...w].slice(0,50),S();break}case"window_updated":{const r=w.findIndex(c=>c.window_id===i.window_id);if(r>=0){const c=w[r].alerts||[];i.alert&&!c.some(h=>h.number===i.alert.number)&&c.push(Xe(i.alert,i.window_id)),w[r]={...w[r],alert_count:i.alert_count||c.length,phases:i.phases||w[r].phases,phase_score:i.phase_score||w[r].phase_score,current_ciso_options:i.ciso_options||w[r].current_ciso_options,...i.expires_at_ms?{expires_at_ms:i.expires_at_ms}:{},...i.window_mode?{window_mode:i.window_mode}:{},alerts:c}}i.alert&&$s(i.window_id,i.alert),S();break}case"window_closed":{Ut(oe,"closed",i.window_id,{reason:i.reason}),Zt(i.window_id,i.reason),re.has(i.window_id)&&(clearTimeout(re.get(i.window_id)),re.delete(i.window_id));const r=w.findIndex(c=>c.window_id===i.window_id);r>=0&&(w[r].confirmed_by!=="operator"?w[r]={...w[r],is_closed:!0,close_reason:i.reason}:w[r]={...w[r],is_closed:!0}),S();break}case"graph_state_update":{ee={nodes:i.nodes||[],edges:i.edges||[],confirmed_hypotheses:i.confirmed_hypotheses||[],kill_chain_progress:i.kill_chain_progress||{},total_evidence_windows:i.total_evidence_windows||0},S();break}case"hypothesis_confirmed":{console.log("[CONFIRM]",i);const r=i.window_id,c=i.label||"",h=i.method||"auto";if(cn(oe,c,i.score),c&&h!=="operator"&&(ge.add(c),je()),r){const u=w.findIndex(m=>m.window_id===r);if(u>=0&&w[u].confirmed_by!=="operator"){const m=h==="timeout"?"⏱":"⚡";w[u]={...w[u],is_closed:!0,close_reason:`${m} ${c}`,confirmed_by:h,confirmed_label:c,confirmed_probability:i.score||i.probability||0}}}S();break}case"dataset_bounds":{if(i.speed_factor!=null&&zs(i.speed_factor),Us(i.dataMinMs,i.dataMaxMs),i.first_alert&&Wt(i.first_alert.number,i.first_alert.category,i.first_alert.type,i.first_alert.timestamp_ms,0,i.total_alerts),(n=i.second_alert)!=null&&n.timestamp_ms){const r=i.second_alert.timestamp_ms-i.first_alert.timestamp_ms,c=Bt(r);jt(i.second_alert.number||"?",i.second_alert.category||"",i.second_alert.type||"",i.second_alert.timestamp_ms,Math.round(r/1e3),c),pe(c)}i.window_mode&&Ke(i.window_mode),ze(0),S();break}case"window_mode_changed":{i.mode&&Ke(i.mode);break}case"next_alert_info":{if(i.is_last)pe(0),Le();else{Wt(i.current_alert_number||"?",i.current_alert_category||"",i.current_alert_type||"",i.current_alert_timestamp_ms,i.current_alert_index,i.total_alerts||i.current_alert_index+1);const r=Bt(i.gap_ms);r>0&&i.gap_ms>0&&(Re=i.gap_ms/r),jt(i.next_alert_number||"?",i.next_alert_category||"",i.next_alert_type||"",i.next_alert_timestamp_ms,Math.round(i.gap_ms/1e3),r),pe(r),Le(),Fs(r,i,()=>ze(i.next_alert_index))}S();break}case"ciso_report":{Qt([i,...Qe()].slice(0,20)),es();const r=i.confirmed_hypothesis_labels||i.confirmed_hypotheses,c=Array.isArray(r)?r.map(m=>typeof m=="string"?m:(m==null?void 0:m.label)??"").filter(Boolean):(o=i.metadata)!=null&&o.selected_hypothesis?[i.metadata.selected_hypothesis]:[],h=(d=(a=i.decision)==null?void 0:a.selected_hypothesis)==null?void 0:d.probability;if(h!=null&&h>0){const m=new Set([...(((l=i.soc_report)==null?void 0:l.trigger_events)||[]).map(v=>String(v.id||"")),...(((p=i.soc_report)==null?void 0:p.raw_alerts)||[]).map(v=>String(v.Number||v.number||""))].filter(Boolean));let f=-1,b=0;w.forEach((v,M)=>{const T=v.confirmed_label||"";if(c.some(L=>T&&(T===L||T.includes(L)||L.includes(T)))){f=M,b=999;return}if(m.size>0){const z=(v.alerts||[]).map(y=>String(y.number||"")).filter(Boolean).filter(y=>m.has(y)).length;z>b&&(b=z,f=M)}}),f>=0&&b>0&&(w[f].confirmed_probability=h,!w[f].confirmed_label&&c[0]&&(w[f].confirmed_label=c[0]))}const u=JSON.stringify(i);ge.forEach(m=>{(c.includes(m)||u.includes(m))&&ge.delete(m)}),je(),S();break}case"done":{pe(0),Le(),w=w.map(r=>r.is_closed?r:{...r,is_closed:!0,close_reason:"⏹ Dataset concluído",confirmed_by:"done"}),S();break}default:ae.trace(oe,`Unhandled: ${_}`)}}catch(_){ln(oe,"SSE parse error",_)}},ie.onerror=()=>{ie==null||ie.close(),ie=null,Ht("reconnecting"),S(),setTimeout(rs,5e3)}}async function bn(){var t;Cs(),vn(),Js(),Bs(),fn(s=>{const n=os.get(s),o=We.get(s);if(!n)return;const a=d=>Object.fromEntries(Object.entries(d).filter(([l,p])=>p!==""&&p!==null&&p!==void 0));window.postMessage({type:"REDSHIFT_WINDOW_CONTEXT",windowId:n.window_id||"",label:n.category||"",probability:0,tier:n.severity||"",cves:[],iocs:o!=null&&o.AffectedAsset?[o.AffectedAsset]:[],phases:n.kill_chain?[n.kill_chain]:n.phases_detected||[],assets:o!=null&&o.AffectedAsset?[o.AffectedAsset]:[],siemAlert:a(o?{alert_number:String(o.Number||o.number||s),external_id:o.ExternalId||"",tlp:o.TLP||"",priority:o.Priority||"",severity:o.Severity||o.severity||"",category:o.Category||o.category||"",type:o.Type||o.type||"",title:o.Title||o.title||"",source:o.Source||o.source||"",tags:o.Tags||"",mitre_attack:o.MitreAttack||"",affected_asset:o.AffectedAsset||"",description:o.Description||"",use_case_tag:o.UseCaseTag||"",kill_chain:n.kill_chain||"",timestamp:o.SiemDetectionTime||n.ts||"",window_id:n.window_id||"",assignee:o.Assignee||"",source_system:"SOC Dashboard Timeline"}:{alert_number:s,category:n.category||"",kill_chain:n.kill_chain||"",severity:n.severity||"",timestamp:n.ts||"",source_system:"SOC Dashboard Timeline"})},"*")}),js(async(s,n)=>{ae.info(oe,`Seek: ${new Date(s).toISOString()} → ${new Date(n).toISOString()}`),Le(),Te.clear(),_e.clear(),w=[],ee=null,me=0,Re=0,Me.clear(),ke.clear(),ge.clear(),je(),re.forEach(d=>clearTimeout(d)),re.clear(),ws([]);const o=document.getElementById("timeline-content"),a=document.getElementById("timeline-alert-count");o&&(o.innerHTML='<div class="timeline-empty-state"><div class="empty-icon">📡</div><div>A reiniciar...</div></div>'),a&&(a.textContent="0"),he("windows-panel","");try{await fetch("/api/agent1/seek",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({start_ms:s,end_ms:n})})}catch(d){ae.warn(oe,`Seek request failed: ${d}`)}S()}),window.addEventListener("wm-filter-change",()=>S()),window.addEventListener("wm-operator-confirmed",s=>{const{windowId:n,label:o}=s.detail,a=w.findIndex(d=>d.window_id===n);a>=0&&(w[a]={...w[a],is_closed:!0,close_reason:`✋ ${o}`,confirmed_by:"operator",confirmed_label:o}),o&&(ge.add(o),je()),S()}),S(),rs();const e=Date.now();setInterval(()=>{const s=Math.floor((Date.now()-e)/1e3),n=document.getElementById("footer-uptime");n&&(n.textContent=s<60?`${s}s`:`${Math.floor(s/60)}m ${s%60}s`)},1e3),setInterval(()=>{me&&Re&&(me+=Re);const s=me||Date.now();document.querySelectorAll(".wm-timer[data-expires]").forEach(n=>{const o=Number(n.dataset.expires);if(!o||isNaN(o))return;const a=Math.max(0,o-s);if(a===0){n.className="wm-timer-expired",n.textContent="⏳ A confirmar automaticamente...",n.removeAttribute("data-expires");return}const d=Math.floor(a/6e4),l=Math.floor(a%6e4/1e3),p=`⏱ ${d}:${l.toString().padStart(2,"0")}`;n.textContent!==p&&(n.textContent=p),n.classList.toggle("critical",a<6e4)})},1e3),(t=document.getElementById("debug-logs-btn"))==null||t.addEventListener("click",()=>ae.downloadLogs()),setInterval(()=>{fetch("/api/stream/status").then(s=>s.json()).then(s=>{const n=document.getElementById("stream-status");n&&(n.textContent=`📡 ${s.connected_clients} clientes · ${s.total_received} alertas`)}).catch(()=>{})},5e3),setInterval(async()=>{try{const s=await fetch("/agent2-reports");if(!s.ok)return;const n=await s.json();n.length!==Qe().length&&(Qt(n),es(),S())}catch{}},5e3)}document.getElementById("app").innerHTML=ps;bn();
