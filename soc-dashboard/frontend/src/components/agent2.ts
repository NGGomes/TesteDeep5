import './agent2.css';
import type { Agent2Report } from '../core/types';
import { esc } from '../core/utils';
import { getCategoryBadge } from '../core/constants';

const _reportMode: Record<string, 'ciso' | 'soc'> = {};

function reportId(r: Agent2Report): string {
 return r.metadata?.window_id
  || r.metadata?.output_timestamp
  || r.metadata?.generated_at
  || JSON.stringify(r.metadata).slice(0, 32);
}

function hypothesisLabel(r: Agent2Report): string {
 return r.metadata?.selected_hypothesis
  || r.decision?.selected_hypothesis?.label
  || r.ciso_report?.primary_hypothesis
  || '—';
}

function riskTier(r: Agent2Report): string {
 return r.ciso_report?.top_risk_tier
  || r.decision?.selected_hypothesis?.risk_tier
  || '';
}

function tierColor(tier: string): string {
 if (tier === 'CRITICAL')    return '#dc2626';
 if (tier === 'HIGH')        return '#ea580c';
 if (tier === 'MEDIUM-HIGH') return '#d97706';
 if (tier === 'MEDIUM')      return '#ca8a04';
 return '#64748b';
}

function fileLinks(r: Agent2Report): {
 ciso: { pdf: string | null; tex: string | null };
 soc:  { pdf: string | null; tex: string | null };
} {
 function _links(texPath: string, pdfPath: string) {
  const texName = texPath ? texPath.split('/').pop()!.split('\\').pop()! : '';
  const pdfName = pdfPath ? pdfPath.split('/').pop()!.split('\\').pop()! : '';
  const renderName = texName || (pdfName ? pdfName.replace('.pdf', '.tex') : '');
  if (!renderName) return { pdf: null, tex: null };
  return {
   pdf: `/render-pdf?file=${encodeURIComponent(renderName)}`,
   tex: texName ? `/reports/agent2/${encodeURIComponent(texName)}` : null,
  };
 }

 const cisoTex = r.metadata?.tex_file     || r.metadata?.source_report || '';
 const cisoPdf = r.metadata?.pdf_file     || '';
 const socTex  = (r.metadata as any)?.soc_tex_file || cisoTex.replace('_ciso.tex', '_soc.tex');
 const socPdf  = '';

 return {
  ciso: _links(cisoTex, cisoPdf),
  soc:  _links(socTex,  socPdf),
 };
}

function isConfirmedReport(r: Agent2Report): boolean {
 return !!(
  r.metadata?.confirmed === true
  || r.metadata?.confirmation_method
  || r.decision?.selected_hypothesis?.label
 );
}

// ── Report cache — id → {cisoHtml, socHtml, mode, pdf, tex, col, label, tier, methodIcon, method} ──
const _reportCache = new Map<string, Record<string, string>>();

// ── Draggable modal ───────────────────────────────────────────────────────────
function _ensureModalContainer(): HTMLElement {
 let el = document.getElementById('r2-modal-root');
 if (!el) {
  el = document.createElement('div');
  el.id = 'r2-modal-root';
  document.body.appendChild(el);
 }
 return el;
}

function _makeDraggable(modal: HTMLElement, handle: HTMLElement): void {
 let ox = 0, oy = 0;
 handle.style.cursor = 'grab';

 handle.addEventListener('mousedown', (e: MouseEvent) => {
  e.preventDefault();
  ox = e.clientX - modal.offsetLeft;
  oy = e.clientY - modal.offsetTop;
  handle.style.cursor = 'grabbing';

  const onMove = (ev: MouseEvent) => {
   const x = Math.max(0, Math.min(window.innerWidth  - modal.offsetWidth,  ev.clientX - ox));
   const y = Math.max(0, Math.min(window.innerHeight - modal.offsetHeight, ev.clientY - oy));
   modal.style.left = x + 'px';
   modal.style.top  = y + 'px';
  };
  const onUp = () => {
   handle.style.cursor = 'grab';
   window.removeEventListener('mousemove', onMove);
   window.removeEventListener('mouseup',   onUp);
  };
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup',   onUp);
 });
}

// ✅ CORRIGIDO: __r2openmode agora apenas chama __r2open
(window as any).__r2openmode = (btn: HTMLElement) => {
 const id   = btn.dataset.rid   || '';
 const mode = (btn.dataset.mode || 'ciso') as 'ciso' | 'soc';
 if (!id) return;

 const data = _reportCache.get(id);
 if (!data) return;

 // Open modal with the correct mode
 (window as any).__r2open(id, mode);
};

(window as any).__r2open = (id: string, initialMode?: 'ciso' | 'soc') => {
 const data = _reportCache.get(id);
 if (!data) return;

 const { cisoHtml, socHtml, cisoPdf, cisoTex, socPdf, socTex, col, label, tier, methodIcon, method } = data;
 const mode = initialMode || data.mode || 'ciso';
 const badgeLabel = getCategoryBadge(label);  // ✅ Badge para o título do modal

 document.getElementById(`r2-modal-${CSS.escape(id)}`)?.remove();

 const modal = document.createElement('div');
 modal.className = 'r2-modal';
 modal.id = `r2-modal-${id}`;
 modal.dataset.modalId = id;
 modal.style.cssText = `left:${Math.max(20, (window.innerWidth - 520) / 2)}px;top:${Math.max(20, (window.innerHeight - 600) / 2)}px`;

 const tierBadge = tier ? `<span class="r2-tier" style="color:${col};border-color:${col}44;background:${col}14">${esc(tier)}</span>` : '';

 const activePdf = mode === 'ciso' ? cisoPdf : socPdf;
 const activeTex = mode === 'ciso' ? cisoTex : socTex;

 // ✅ ALTERADO: usa badgeLabel em vez de label no título
 modal.innerHTML = `
  <div class="r2-modal-handle">
   <div class="r2-modal-title">
    ${tierBadge}
    <span class="r2-modal-label">${esc(badgeLabel)}</span>
   </div>
   <div class="r2-modal-meta">
    <span class="r2-confirm-badge">${methodIcon} ${esc(method)}</span>
   </div>
   <button class="r2-modal-close" onclick="this.closest('.r2-modal')?.remove()" title="Fechar">✕</button>
  </div>
  <div class="r2-modal-body">
   <div class="r2-tabs" style="margin-bottom:8px">
    <button class="r2-tab ${mode === 'ciso' ? 'active' : ''}"
     onclick="window.__r2modaltab(this,'ciso')">CISO</button>
    <button class="r2-tab ${mode === 'soc' ? 'active' : ''}"
     onclick="window.__r2modaltab(this,'soc')">SOC</button>
   </div>
   <div class="r2-modal-content" style="${mode === 'ciso' ? '' : 'display:none'}">${cisoHtml}</div>
   <div class="r2-modal-content" style="${mode === 'soc'  ? '' : 'display:none'}">${socHtml}</div>
   <div class="r2-actions r2-modal-actions"
     style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border2)"
     data-ciso-pdf="${esc(cisoPdf)}" data-ciso-tex="${esc(cisoTex)}"
     data-soc-pdf="${esc(socPdf)}"   data-soc-tex="${esc(socTex)}">
    ${activePdf ? `<a class="r2-btn r2-btn-pdf" href="${esc(activePdf)}" target="_blank">📄 PDF</a>` : '<span class="r2-btn r2-btn-disabled">📄 PDF</span>'}
    ${activeTex ? `<a class="r2-btn r2-btn-tex" href="${esc(activeTex)}" target="_blank">{} .tex</a>` : '<span class="r2-btn r2-btn-disabled">{} .tex</span>'}
   </div>
  </div>`;

 _ensureModalContainer().appendChild(modal);
 _makeDraggable(modal, modal.querySelector('.r2-modal-handle') as HTMLElement);
};

(window as any).__r2modaltab = (btn: HTMLElement, mode: 'ciso' | 'soc') => {
 const modal = btn.closest('.r2-modal') as HTMLElement;
 if (!modal) return;

 modal.querySelectorAll('.r2-tab').forEach(t => t.classList.remove('active'));
 btn.classList.add('active');

 const panels = modal.querySelectorAll('.r2-modal-content') as NodeListOf<HTMLElement>;
 panels.forEach((el, i) => {
  el.style.display = (i === 0 && mode === 'ciso') || (i === 1 && mode === 'soc') ? '' : 'none';
 });

 const actions = modal.querySelector('.r2-modal-actions') as HTMLElement;
 if (!actions) return;
 const pdf = actions.dataset[mode === 'ciso' ? 'cisoPdf' : 'socPdf'] || '';
 const tex = actions.dataset[mode === 'ciso' ? 'cisoTex' : 'socTex'] || '';
 actions.innerHTML =
  (pdf ? `<a class="r2-btn r2-btn-pdf" href="${esc(pdf)}" target="_blank">📄 PDF</a>` : '<span class="r2-btn r2-btn-disabled">📄 PDF</span>') +
  (tex ? `<a class="r2-btn r2-btn-tex" href="${esc(tex)}" target="_blank">{} .tex</a>` : '<span class="r2-btn r2-btn-disabled">{} .tex</span>');
};

(window as any).__r2toggle = (_id: string, _btn: HTMLButtonElement) => {};

export function renderAgent2Panel(
 _hyps: any,
 _selectedHyp: any,
 reports: Agent2Report[],
 _a2ReportMode: any
): string {
 const confirmed = (reports || []).filter(isConfirmedReport);

 if (confirmed.length === 0) {
  return `<div class="r2-empty">
   <span style="font-size:20px;opacity:.35">📋</span>
   <span>Sem relatórios confirmados ainda.</span>
  </div>`;
 }

 return confirmed.map(r => {
  const id    = reportId(r);
  const label = hypothesisLabel(r);
  const badgeLabel = getCategoryBadge(label);  // ✅ ADICIONADO
  const tier  = riskTier(r);
  const col   = tierColor(tier);
  const mode  = _reportMode[id] || 'ciso';
  const links = fileLinks(r);

  const ts = r.metadata?.output_timestamp || r.metadata?.generated_at || '';
  const tsDisplay = ts
   ? new Date(ts).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' })
   : '—';

  const rawMethod  = r.metadata?.confirmation_method || 'auto';
  const method     = rawMethod.includes('operator') ? 'operator'
          : rawMethod.includes('timeout')  ? 'timeout'
          : 'auto';
  const methodIcon = method === 'operator' ? '✋' : method === 'timeout' ? '⏱' : '⚡';
  const llmBadge   = r.metadata?.llm_used
   ? `<span class="r2-badge llm">🤖 ${esc(r.metadata?.model_used || 'LLM')}</span>`
   : `<span class="r2-badge rule">⚡ Rule</span>`;
  const prob       = r.decision?.selected_hypothesis?.probability;
  const probPct    = prob != null ? `${Math.round(prob * 100)}%` : '';

  
  // ── CISO content ──────────────────────────────────────────────────────────
  const cisoSummary = r.ciso_report?.executive_summary
   || r.ciso_report?.summary
   || (r as any).executive_summary
   || '—';
  const topCats = (
   r.ciso_report?.top_categories
   || (r as any).top_hypotheses?.map((h: any) => [h.label || h.category, h.confidence || h.probability] as [string, number])
   || []
  ).slice(0, 3) as [string, number][];
  const bizImpact    = r.ciso_report?.business_impact || '';
  const regulatory   = r.ciso_report?.regulatory_implications || '';
  const recommendations = (r.ciso_report?.strategic_recommendations || []).slice(0, 4);

  // ── SOC content ──────────────────────────────────────────────────────────
  const totalAlerts  = r.soc_report?.total_alerts ?? '—';
  const assets       = (r.soc_report?.affected_assets || []).slice(0, 4);
  const cves         = r.soc_report?.ioc_bundle?.cve_ids || r.soc_report?.detected_cves || [];
  const mitre        = (r.soc_report?.mitre_techniques || []).slice(0, 5);
  const phases       = (r.soc_report?.kill_chain_phases || []);
  const remediation  = (r.soc_report?.remediation_steps || []).slice(0, 4);
  const ips          = (r.soc_report?.ioc_bundle?.ipv4_addresses || []).slice(0, 4);
  const fqdns        = (r.soc_report?.ioc_bundle?.fqdns || []).slice(0, 4);
  const timeline     = (r.soc_report?.timeline || []).slice(0, 5);

  const cisoHtml = `
   <div class="r2-section-lbl">Executive Summary</div>
   <div class="r2-summary">${esc(cisoSummary)}</div>

   ${topCats.length ? `
   <div class="r2-section-lbl">Top Hipóteses</div>
   <div class="r2-cats">
    ${topCats.map(([cat, p]) => `
     <div class="r2-cat-row">
      <span class="r2-cat-name">${esc(String(cat))}</span>
      <div class="r2-cat-bar-wrap">
       <div class="r2-cat-bar" style="width:${Math.round(Number(p)*100)}%"></div>
      </div>
      <span class="r2-cat-pct">${Math.round(Number(p)*100)}%</span>
     </div>`).join('')}
   </div>` : ''}

   ${bizImpact ? `
   <div class="r2-section-lbl">Impacto no Negócio</div>
   <div class="r2-text">${esc(bizImpact)}</div>` : ''}

   ${regulatory ? `
   <div class="r2-section-lbl">Implicações Regulatórias</div>
   <div class="r2-text r2-text-warn">${esc(regulatory)}</div>` : ''}

   ${recommendations.length ? `
   <div class="r2-section-lbl">Recomendações</div>
   <ol class="r2-list">
    ${recommendations.map(s => `<li>${esc(s)}</li>`).join('')}
   </ol>` : ''}`;

  const socHtml = `
   <div class="r2-kv-grid">
    <div class="r2-kv"><span class="r2-k">Alertas</span><span class="r2-v">${totalAlerts}</span></div>
    ${phases.length ? `<div class="r2-kv"><span class="r2-k">Kill-Chain</span><span class="r2-v">${esc(phases.join(' → '))}</span></div>` : ''}
   </div>

   ${assets.length ? `
   <div class="r2-section-lbl">Assets Afectados</div>
   <div class="r2-tags">${assets.map(a => `<span class="r2-tag">${esc(a)}</span>`).join('')}</div>` : ''}

   ${mitre.length ? `
   <div class="r2-section-lbl">MITRE ATT&CK</div>
   <div class="r2-tags">${mitre.map(t => `<span class="r2-tag mitre">${esc(t)}</span>`).join('')}</div>` : ''}

   ${cves.length ? `
   <div class="r2-section-lbl">CVEs</div>
   <div class="r2-tags">${cves.slice(0,5).map(c => `<span class="r2-tag cve">${esc(c)}</span>`).join('')}</div>` : ''}

   ${(ips.length || fqdns.length) ? `
   <div class="r2-section-lbl">IoCs</div>
   <div class="r2-tags">
    ${ips.map(ip => `<span class="r2-tag ioc">${esc(ip)}</span>`).join('')}
    ${fqdns.map(d => `<span class="r2-tag ioc">${esc(d)}</span>`).join('')}
   </div>` : ''}

   ${timeline.length ? `
   <div class="r2-section-lbl">Timeline</div>
   <div class="r2-timeline">
    ${timeline.map(ev => `
     <div class="r2-tl-row">
      <span class="r2-tl-ts">${esc(ev.timestamp)}</span>
      <span class="r2-tl-ev">${esc(ev.event)}</span>
     </div>`).join('')}
   </div>` : ''}

   ${remediation.length ? `
   <div class="r2-section-lbl">Remediação</div>
   <ol class="r2-list">
    ${remediation.map(s => `<li>${esc(s)}</li>`).join('')}
   </ol>` : ''}`;

  // Store in cache for modal rendering
  _reportCache.set(id, {
   cisoHtml, socHtml, mode,
   cisoPdf: links.ciso.pdf || '', cisoTex: links.ciso.tex || '',
   socPdf:  links.soc.pdf  || '', socTex:  links.soc.tex  || '',
   col, label, tier, methodIcon, method,
  });

  const alertNumbers = (() => {
      // Tentar trigger_events primeiro
      const triggers = r.soc_report?.trigger_events || [];
      if (triggers.length > 0) {
          return triggers.map(t => t.id).filter(id => id && id !== '—').join(', ');
      }
      // Fallback: raw_alerts com type assertion
      const rawAlerts = r.soc_report?.raw_alerts || [];
      if (rawAlerts.length > 0) {
          return rawAlerts.map((a: any) => a.Number || a.number || '').filter(n => n).join(', ');
      }
      return '';
  })();
  
  // Window context from metadata
  const windowId   = r.metadata?.window_id || '';
  const alertCount = r.metadata?.alert_count || 0;
  const wPhases    = r.metadata?.phases || [];
  const phaseScore = r.metadata?.phase_score || 0;
  const wStart     = r.metadata?.window_start_ms ? new Date(r.metadata.window_start_ms).toLocaleTimeString('pt-PT').slice(0,5) : '';
  const wEnd       = r.metadata?.window_end_ms   ? new Date(r.metadata.window_end_ms).toLocaleTimeString('pt-PT').slice(0,5)   : '';

  const windowCtxHtml = (alertCount || windowId) ? `
 <div class="r2-window-ctx">
  ${windowId   ? `<span class="r2-wid" title="Window ID">${esc(windowId.slice(0,8))}</span>` : ''}
  ${alertCount ? `<span class="r2-meta-chip">📊 ${alertCount} alertas</span>` : ''}
  ${phaseScore ? `<span class="r2-meta-chip">🎯 Score: ${phaseScore}</span>` : ''}
  ${wPhases.length ? `<span class="r2-meta-chip">🔗 ${wPhases.slice(0,3).join(' → ')}</span>` : ''}
  ${wStart     ? `<span class="r2-meta-chip">📅 ${wStart}${wEnd ? ` → ${wEnd}` : ''}</span>` : ''}
 </div>` : '';

  const alertNumbersHtml = alertNumbers ? `
<div class="r2-alert-numbers" style="margin-top:6px;padding-top:4px;border-top:1px solid var(--border2);">
  <span style="font-size:8px;font-family:var(--mono);color:var(--text4);">📋 Alertas:</span>
  <span style="font-size:8px;font-family:var(--mono);color:var(--cyan-hi);
               word-break:break-all;white-space:normal;display:block;margin-top:2px;">
    ${esc(alertNumbers)}
  </span>
</div>` : '';

  // ✅ ALTERADO: usa badgeLabel no card
  return `
<div class="r2-card" data-report-id="${esc(id)}" style="border-left-color:${col}">
    <div class="r2-label-row">
        ${tier ? `<span class="r2-tier" style="color:${col};border-color:${col}44;background:${col}14">${esc(tier)}</span>` : ''}
        ${probPct ? `<span class="r2-prob" style="color:${col};font-weight:800;font-size:11px">${probPct}</span>` : ''}
        <span class="r2-hyp" title="${esc(label)}">${esc(badgeLabel)}</span>
        <button class="r2-toggle-btn" title="Abrir relatório completo" onclick="window.__r2open('${esc(id)}')">⊞</button>
    </div>
    <div class="r2-meta-row" style="margin-top:5px">
        <span class="r2-confirm-badge">${methodIcon} ${esc(method)}</span>
        ${llmBadge}
    </div>
    ${windowCtxHtml}
    ${alertNumbersHtml}
    <div class="r2-ts" style="margin-top:4px">${tsDisplay}</div>
</div>`;
 }).join('');
}

export function wireAgent2Events(): void {
 (window as any).__r2tab = (id: string, mode: 'ciso' | 'soc') => {
  _reportMode[id] = mode as 'ciso' | 'soc';
 };
}