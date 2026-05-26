// content.ts — RedShift CVE Agent
// Injected into: Kibana + SOC Dashboard (localhost:5001)
// Communicates with background.ts via chrome.runtime.sendMessage
// Communicates with the dashboard via window.postMessage (REDSHIFT_* protocol)

const CVE_REGEX = /CVE-\d{4}-\d{4,}/gi;

let detectedCves: Set<string> = new Set();
let injectedNodes: Set<Element> = new Set();

// ── Dashboard → Extension push context ───────────────────────────────────────
// The SOC dashboard sends window context proactively when a window becomes
// confirmable (topPct >= 75%). No user action required.

window.addEventListener('message', (event) => {
  // Only accept messages from the same origin (dashboard)
  if (event.source !== window) return;
  const msg = event.data;
  if (!msg || typeof msg !== 'object') return;

  if (msg.type === 'REDSHIFT_WINDOW_CONTEXT') {
    handleWindowContext(msg);
  }
  if (msg.type === 'REDSHIFT_CLEAR_CONTEXT') {
    chrome.runtime.sendMessage({ type: 'CLEAR_BADGE' }).catch(() => {});
  }
});

function handleWindowContext(ctx: {
  type: string;
  windowId: string;
  label: string;
  probability: number;
  tier: string;
  cves: string[];
  iocs: string[];
  phases: string[];
  assets: string[];
  siemAlert?: Record<string, unknown>;
}): void {
  try {
    const extractedCves: string[] = [...(ctx.cves || [])];
    if (ctx.siemAlert) {
      const searchText = [
        ctx.siemAlert['title']       || '',
        ctx.siemAlert['description'] || '',
        ctx.siemAlert['tags']        || '',
      ].join(' ');
      const cveRe = /CVE-\d{4}-\d{4,}/gi;
      let m: RegExpExecArray | null;
      while ((m = cveRe.exec(searchText)) !== null) {
        const c = m[0].toUpperCase();
        if (!extractedCves.includes(c)) extractedCves.push(c);
      }
    }
    chrome.storage.local.set({
      pendingWindowContext: {
        windowId:    ctx.windowId,
        label:       ctx.label,
        probability: ctx.probability,
        tier:        ctx.tier,
        cves:        extractedCves,
        iocs:        ctx.iocs || [],
        phases:      ctx.phases || [],
        assets:      ctx.assets || [],
        siemAlert:   ctx.siemAlert || null,
        receivedAt:  Date.now(),
      },
    });
    if (extractedCves.length > 0) {
      _runtimeSend({ type: 'CVE_DETECTED', cveIds: extractedCves });
    } else {
      _runtimeSend({ type: 'WINDOW_CONTEXT_READY' });
    }
  } catch { /* context invalidated */ }
}

// ── CVE scanning (existing logic) ────────────────────────────────────────────
function init(): void {
  scanForCves();
  setupMutationObserver();
}

function scanForCves(): void {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: (node) => {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        const tag = parent.tagName.toLowerCase();
        if (['script', 'style', 'noscript'].includes(tag)) return NodeFilter.FILTER_REJECT;
        if (parent.dataset.rsProcessed) return NodeFilter.FILTER_REJECT;
        CVE_REGEX.lastIndex = 0;
        return CVE_REGEX.test(node.textContent ?? '')
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_SKIP;
      },
    }
  );

  const nodesToProcess: Text[] = [];
  let node: Node | null;
  CVE_REGEX.lastIndex = 0;
  while ((node = walker.nextNode())) nodesToProcess.push(node as Text);
  nodesToProcess.forEach(processTextNode);

  if (detectedCves.size > 0) notifyBackground();
}

function processTextNode(textNode: Text): void {
  const parent = textNode.parentElement;
  if (!parent || parent.dataset.rsProcessed) return;
  parent.dataset.rsProcessed = '1';

  const text = textNode.textContent ?? '';
  CVE_REGEX.lastIndex = 0;

  const parts: (string | HTMLElement)[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  CVE_REGEX.lastIndex = 0;
  while ((match = CVE_REGEX.exec(text)) !== null) {
    const cveId = match[0].toUpperCase();
    detectedCves.add(cveId);
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(createCveChip(cveId));
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));

  if (parts.length > 1) {
    const fragment = document.createDocumentFragment();
    parts.forEach(part => {
      if (typeof part === 'string') fragment.appendChild(document.createTextNode(part));
      else { fragment.appendChild(part); injectedNodes.add(part); }
    });
    parent.replaceChild(fragment, textNode);
  }
}

function createCveChip(cveId: string): HTMLElement {
  const chip = document.createElement('span');
  chip.style.cssText = `
    display:inline-flex;align-items:center;gap:4px;
    font-family:'JetBrains Mono',monospace;font-size:0.9em;font-weight:600;
    color:#fca5a5;background:rgba(232,25,44,0.12);border:1px solid rgba(232,25,44,0.25);
    border-radius:4px;padding:1px 6px;cursor:default;position:relative;
  `;
  chip.textContent = cveId;
  chip.title = `Clica para analisar ${cveId} com RedShift`;

  const btn = document.createElement('button');
  btn.textContent = '▸';
  btn.title = `Analisar ${cveId} com RedShift`;
  btn.style.cssText = `
    background:#e8192c;border:none;border-radius:3px;color:white;
    font-size:10px;padding:0 5px;cursor:pointer;line-height:1.5;
    margin-left:2px;transition:background 0.15s;
  `;
  btn.addEventListener('mouseenter', () => { btn.style.background = '#b5111f'; });
  btn.addEventListener('mouseleave', () => { btn.style.background = '#e8192c'; });
  btn.addEventListener('click', (e) => {
    e.stopPropagation(); e.preventDefault();
    chrome.storage.local.set({ pendingCve: cveId }, () => {
      chrome.runtime.sendMessage({ type: 'OPEN_WITH_CVE', cveId }).catch(() => {});
    });
  });

  chip.appendChild(btn);
  return chip;
}

function _runtimeSend(msg: object): void {
  try {
    chrome.runtime.sendMessage(msg).catch(() => {});
  } catch {
    // Extension context invalidated (e.g. after reload) — ignore silently
  }
}

function notifyBackground(): void {
  _runtimeSend({ type: 'CVE_DETECTED', cveIds: [...detectedCves] });
}

function openExtensionWithCve(cveId: string): void {
  try {
    chrome.storage.local.set({ pendingCve: cveId }, () => {
      _runtimeSend({ type: 'OPEN_WITH_CVE', cveId });
    });
  } catch { /* context invalidated */ }
}

function setupMutationObserver(): void {
  const observer = new MutationObserver((mutations) => {
    if (mutations.some(m => m.addedNodes.length > 0)) {
      clearTimeout((window as any)._rsScanTimer);
      (window as any)._rsScanTimer = setTimeout(scanForCves, 500);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

try {
  chrome.runtime.onMessage.addListener(
    (message: { type: string }, _sender, sendResponse) => {
      if (message.type === 'GET_DETECTED_CVES') {
        sendResponse({ cves: [...detectedCves] });
      }
      return true;
    }
  );
} catch { /* context invalidated */ }

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

export {};