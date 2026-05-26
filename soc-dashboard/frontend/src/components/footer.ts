export function renderConnectionBadge(connection: string): string {
const map: Record<string, { text: string; color: string; animate: boolean }> = {
connecting: { text: 'Connecting…', color: '#d97706', animate: true },
connected: { text: 'Live', color: '#16a34a', animate: true },
reconnecting: { text: 'Reconnecting…', color: '#ea580c', animate: true },
done: { text: 'Processing complete', color: '#7c3aed', animate: false },
error: { text: 'Connection error', color: '#dc2626', animate: false },
};

const s = map[connection] ?? map['connecting'];

const dot = s.animate
? `<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${s.color};animation:livepulse 2s ease-in-out infinite;margin-right:5px"></span>`
: `<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${s.color};margin-right:5px"></span>`;

return `${dot}<span>${s.text}</span>`;
}

export function renderFooterChips(
totalHypotheses: number,
severeCount: number,
noiseCount: number,
mitreTechs: number,
totalReceived: number
): string {
return `
<span class="fchip">Hypotheses <span class="val">${totalHypotheses}</span></span>
<span class="fchip">Severe <span class="val" style="color:#f87171">${severeCount}</span></span>
<span class="fchip">Noise <span class="val" style="color:#38bdf8">${noiseCount}</span></span>
<span class="fchip">MITRE <span class="val">${mitreTechs}</span></span>
<span class="fchip">Alerts <span class="val">${totalReceived}</span></span>
<span class="fchip">ENISA · MITRE ATT&CK · NIS2</span>
`;
}

export function startUptimeClock(elementId: string = 'footer-uptime'): void {
const startTime = Date.now();
setInterval(() => {
const elapsed = Math.floor((Date.now() - startTime) / 1000);
const display = elapsed < 60
? `${elapsed}s`
: `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
const el = document.getElementById(elementId);
if (el) el.textContent = `Session ${display}`;
}, 1000);
}
