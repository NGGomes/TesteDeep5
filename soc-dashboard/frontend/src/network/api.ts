// Send the active window start and requested duration to the server
export async function sendSliceUpdate(windowStartMs: number, durationMs: number): Promise<void> {
try {
 await fetch('/slice-update', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
  windowStartMs,
  durationMs,
  windowStartIso: new Date(windowStartMs).toISOString(),
  windowEndMs:    windowStartMs + durationMs,
  windowEndIso:   new Date(windowStartMs + durationMs).toISOString(),
 }),
 });
} catch (err) {
 console.warn('[API] sendSliceUpdate failed:', err);
}
}

// Fetch the current slice-meta from the server (used on init)
export async function fetchSliceMeta(): Promise<Record<string, unknown> | null> {
try {
 const r = await fetch('/slice-meta');
 if (r.ok) return r.json();
} catch { }
return null;
}

// Agent2 report fetch
export async function fetchAgent2Reports(): Promise<unknown[] | null> {
try {
 const r = await fetch('/agent2-reports');
 if (r.ok) return r.json();
} catch { }
return null;
}

