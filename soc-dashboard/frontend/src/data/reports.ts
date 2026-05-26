export function fmtDate(ms: number): string {
return ms ? new Date(ms).toISOString().replace('T', ' ').replace('Z', '').slice(0, 19) : '—';
}

