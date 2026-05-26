import "./graph_viz.css";
import type { HypothesisGraphState } from '../core/types';
import { esc } from '../core/utils';

export function renderHypothesisGraph(graphState: HypothesisGraphState | null): string {
 if (!graphState || !graphState.nodes || graphState.nodes.length === 0) {
  return '<div class="empty-state">Aguardando evidências para construir o grafo de hipóteses...</div>';
 }

 const nodes = graphState.nodes;
 const edges = graphState.edges || [];
 const killChainProgress = graphState.kill_chain_progress || {};

 const phasesOrder = ['RECON', 'INITIAL_ACCESS', 'EXECUTION', 'PERSISTENCE', 'LATERAL_MOVEMENT', 'EXFILTRATION', 'IMPACT'];
 
 const killChainHtml = `
  <div style="margin-bottom: 20px">
   <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 12px">
    🧬 Kill Chain Progress (Global)
   </div>
   <div style="display: flex; flex-wrap: wrap; gap: 8px">
    ${phasesOrder.map((phase) => {
     const progress = killChainProgress[phase] || 0;
     const color = progress > 0.7 ? '#22c55e' : progress > 0.3 ? '#eab308' : '#475569';
     const isComplete = progress >= 0.9;
     return `
      <div style="flex: 1; min-width: 100px; background: var(--bg3); border-radius: 8px; padding: 8px; text-align: center; border-left: 3px solid ${color}">
       <div style="font-size: 9px; font-family: monospace; color: ${color}; font-weight: 700">${phase.replace('_', ' ')}</div>
       <div style="font-size: 14px; font-weight: 700; color: ${color}">${Math.round(progress * 100)}%</div>
       <div style="height: 4px; background: var(--bg2); border-radius: 2px; margin-top: 4px; overflow: hidden">
        <div style="width: ${progress * 100}%; height: 100%; background: ${color}; border-radius: 2px"></div>
       </div>
       ${isComplete ? '<span style="font-size: 8px; color: #22c55e">✓ Completed</span>' : ''}
      </div>
     `;
    }).join('')}
   </div>
  </div>
 `;

 const topNodes = nodes
  .sort((a, b) => b.cumulative_score - a.cumulative_score)
  .slice(0, 8);

 const nodesHtml = `
  <div style="margin-bottom: 20px">
   <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 12px">
    🎯 Top Hypotheses (Global Graph)
   </div>
   <div style="display: flex; flex-wrap: wrap; gap: 10px">
    ${topNodes.map(node => {
     const tierColor = node.risk_tier === 'CRITICAL' ? '#dc2626' 
      : node.risk_tier === 'HIGH' ? '#ea580c'
      : node.risk_tier === 'MEDIUM-HIGH' ? '#d97706'
      : node.risk_tier === 'MEDIUM' ? '#ca8a04'
      : '#475569';
     return `
      <div style="background: var(--bg2); border: 1px solid ${node.confirmed ? '#22c55e' : 'var(--border2)'}; border-radius: 8px; padding: 10px 14px; min-width: 180px; flex: 1">
       <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px">
        <span style="font-size: 12px; font-weight: 700; color: var(--text)">${esc(node.label)}</span>
        ${node.confirmed ? '<span style="font-size: 10px; background: #22c55e20; color: #22c55e; padding: 2px 6px; border-radius: 4px">✓ Confirmed</span>' : ''}
       </div>
       <div style="display: flex; justify-content: space-between; align-items: center">
        <span style="font-size: 20px; font-weight: 700; color: ${tierColor}">${Math.round(node.cumulative_score * 100)}%</span>
        <span style="font-size: 10px; color: var(--text4)">${node.evidence_count} evidências</span>
       </div>
       <div style="height: 4px; background: var(--bg3); border-radius: 2px; margin-top: 6px; overflow: hidden">
        <div style="width: ${node.cumulative_score * 100}%; height: 100%; background: ${tierColor}; border-radius: 2px"></div>
       </div>
       <div style="font-size: 9px; color: var(--text4); margin-top: 4px">Risk: ${node.risk_tier}</div>
      </div>
     `;
    }).join('')}
   </div>
  </div>
 `;

 const edgesHtml = edges.length > 0 ? `
  <div style="margin-bottom: 20px">
   <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text3); margin-bottom: 12px">
    🔗 Phase Transitions (Evidence Weight)
   </div>
   <div style="display: flex; flex-wrap: wrap; gap: 6px">
    ${edges.slice(0, 15).map(edge => `
     <span style="background: var(--bg3); padding: 4px 10px; border-radius: 4px; font-family: monospace; font-size: 10px">
      ${esc(edge.source)} → ${esc(edge.target)}
      <span style="color: #22c55e; margin-left: 6px">${Math.round(edge.weight * 100)}%</span>
      <span style="color: var(--text4); font-size: 8px">(${edge.evidence_count}x)</span>
     </span>
    `).join('')}
   </div>
  </div>
 ` : '';

 const evidenceCount = graphState.total_evidence_windows || 0;

 const statsHtml = `
  <div style="display: flex; gap: 12px; margin-bottom: 20px; padding: 12px; background: var(--bg3); border-radius: 8px">
   <div>
    <div style="font-size: 10px; color: var(--text4)">Total Nodes</div>
    <div style="font-size: 24px; font-weight: 700; color: var(--cyan-hi)">${nodes.length}</div>
   </div>
   <div>
    <div style="font-size: 10px; color: var(--text4)">Transitions</div>
    <div style="font-size: 24px; font-weight: 700; color: var(--cyan-hi)">${edges.length}</div>
   </div>
   <div>
    <div style="font-size: 10px; color: var(--text4)">Evidence Windows</div>
    <div style="font-size: 24px; font-weight: 700; color: var(--cyan-hi)">${evidenceCount}</div>
   </div>
   <div>
    <div style="font-size: 10px; color: var(--text4)">Confirmed</div>
    <div style="font-size: 24px; font-weight: 700; color: #22c55e">${graphState.confirmed_hypotheses?.length || 0}</div>
   </div>
  </div>
 `;

 return `
  <div class="hypothesis-graph-container">
   ${statsHtml}
   ${killChainHtml}
   ${nodesHtml}
   ${edgesHtml}
   <div style="font-size: 10px; color: var(--text4); padding: 8px; text-align: center; border-top: 1px solid var(--border2); margin-top: 12px">
    🧠 Hypothesis Graph — Memória global fora das janelas. Janelas produzem evidência, o grafo possui a verdade.
   </div>
  </div>
 `;
}
